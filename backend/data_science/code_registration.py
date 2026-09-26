import base64, tempfile
from pathlib import Path
from django.db import transaction
from django.utils import timezone
from data_model.models import FieldAsset, TableAsset
from dependencies.models import AssetDependency
from dependencies.services import create_dependency
from platform_ops.storage import put_file
from common.models import ScriptArtifact
from .models import DatasetDefinition, ModelDefinition, ModelRun, ModelVersion
from .ml_services import ensure_model_data_asset


def _algorithm(meta):
    cls=(meta.get("class_name") or "PythonEstimator").upper()
    module=(meta.get("module") or "").lower()
    if "xgboost" in module or cls.startswith("XGB"):
        return "XGBOOST_CLASSIFIER" if "CLASSIFIER" in cls else "XGBOOST_REGRESSOR"
    if "RANDOMFORESTCLASSIFIER" in cls: return ModelDefinition.Algorithm.RANDOM_FOREST_CLASSIFIER
    if "RANDOMFORESTREGRESSOR" in cls: return ModelDefinition.Algorithm.RANDOM_FOREST_REGRESSOR
    if "LOGISTICREGRESSION" in cls: return ModelDefinition.Algorithm.LOGISTIC_REGRESSION
    if cls=="LINEARREGRESSION": return ModelDefinition.Algorithm.LINEAR_REGRESSION
    return "PYTHON_ESTIMATOR"


def _source_table(block, feature_names, target_name):
    qs=TableAsset.objects.filter(data_source__workspace=block.workspace).prefetch_related("fields")
    wanted=set(feature_names or []) | ({target_name} if target_name else set())
    candidates=[]
    for table in qs:
        names={f.name for f in table.fields.all()} | {getattr(f,"technical_name","") for f in table.fields.all()}
        score=len(wanted & names)
        if wanted and score==len(wanted): return table
        if score: candidates.append((score,table))
    return max(candidates,key=lambda x:x[0])[1] if candidates else None

@transaction.atomic
def register_code_model(block,user,meta,display_name=None):
    if meta.get("kind")!="ml_model": raise ValueError("The selected variable is not an ML model.")
    features=meta.get("feature_names") or []
    target_name=meta.get("target_name") or ""
    table=_source_table(block,features,target_name)
    if not table: raise ValueError("Could not identify the source table for this model. Train with DataFrame columns from a workspace table.")
    field_map={f.name:f for f in table.fields.all()}
    target=field_map.get(target_name)
    if not target: raise ValueError(f"Could not identify target field '{target_name}' in the source table.")
    feature_fields=[field_map[n] for n in features if n in field_map and n!=target_name]
    if not feature_fields: raise ValueError("Could not identify model feature fields in the source table.")
    base=(display_name or meta.get("name") or meta.get("class_name") or "Python model").strip()
    dataset,_=DatasetDefinition.objects.get_or_create(workspace=block.workspace,name=f"{base} dataset",defaults={"source_table":table,"created_by":user,"description":f"Dataset inferred from Code block {block.id}."})
    model=ModelDefinition.objects.filter(workspace=block.workspace,name=base).first()
    task=meta.get("task_type") or ("CLASSIFICATION" if "Classifier" in (meta.get("class_name") or "") else "REGRESSION")
    if not model:
        model=ModelDefinition.objects.create(workspace=block.workspace,dataset=dataset,name=base,description=f"Registered from Code block {block.id}.",task_type=task,algorithm=_algorithm(meta),target=target,parameters={"source":"CODE","python_class":meta.get("class_name"),"python_module":meta.get("module")},created_by=user)
    else:
        model.dataset=dataset; model.task_type=task; model.algorithm=_algorithm(meta); model.target=target; model.save(update_fields=["dataset","task_type","algorithm","target","updated_at"])
    model.features.set(feature_fields)
    model_asset=ensure_model_data_asset(model)
    metrics=dict(meta.get("metrics") or {})
    for key in ("confusion_matrix","classification_report","class_labels","class_distribution","roc_curve","precision_recall_curve","probability_distribution","feature_importance","probability_warning","evaluation_warning"):
        if meta.get(key) is not None: metrics[key]=meta[key]
    metrics["runtime"]={"source":"CODE","python_class":meta.get("class_name"),"python_module":meta.get("module"),"environment":"workspace Python environment"}
    train_rows=int(meta.get("train_row_count") or 0); test_rows=int(meta.get("test_row_count") or 0)
    run=ModelRun.objects.create(model=model,status=ModelRun.Status.SUCCESS,metrics=metrics,parameters_snapshot=model.parameters,row_count=train_rows+test_rows,train_row_count=train_rows,test_row_count=test_rows,started_at=timezone.now(),finished_at=timezone.now())
    next_version=(model.versions.order_by("-version").values_list("version",flat=True).first() or 0)+1
    raw=base64.b64decode(meta["artifact_base64"])
    with tempfile.NamedTemporaryFile(suffix=".joblib",delete=False) as tmp:
        tmp.write(raw); tmp_path=Path(tmp.name)
    try: uri=put_file(f"models/{model.id}/v{next_version}/model.joblib",tmp_path,"application/octet-stream")
    finally: tmp_path.unlink(missing_ok=True)
    version=ModelVersion.objects.create(model=model,run=run,version=next_version,artifact_path=uri,metrics=metrics,feature_names=features,target_name=target_name,algorithm=model.algorithm,sklearn_version="code-environment")
    ScriptArtifact.objects.update_or_create(script_block=block,artifact_type=ScriptArtifact.Type.ML_MODEL,name=meta.get("name") or base,defaults={"object_type":"MODEL_DEFINITION","object_id":str(model.id),"metadata":{"model_version_id":str(version.id),"source":"CODE","variable":meta.get("name")}})
    create_dependency(workspace=block.workspace,upstream=table.data_asset,downstream=model_asset,dependency_type=AssetDependency.DependencyType.MODEL_INPUT,refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,metadata={"source":"CODE","script_block_id":str(block.id)})
    return {"model_id":str(model.id),"model_version_id":str(version.id),"run_id":str(run.id),"name":model.name,"version":version.version,"metrics":metrics,"task_type":model.task_type,"algorithm":model.algorithm}
