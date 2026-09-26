from pathlib import Path
import joblib, pandas as pd, sklearn
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, classification_report, roc_auc_score, roc_curve, precision_recall_curve, average_precision_score, log_loss, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from datasources.models import DataAsset
from dependencies.models import AssetDependency
from dependencies.services import create_dependency, ensure_asset_state, record_change
from execution.services import mark_running, mark_success, update_progress, emit_event, report_metric, ensure_not_cancelled
from platform_ops.storage import materialize, put_file
from platform_ops.parquet import dataframe_to_parquet_artifact
from .data_io import dataset_to_dataframe, save_dataframe_csv
from .models import ModelDefinition, ModelRun, ModelVersion, PredictionAsset

ALGORITHM_FACTORY={
    ModelDefinition.Algorithm.LOGISTIC_REGRESSION:LogisticRegression,
    ModelDefinition.Algorithm.RANDOM_FOREST_CLASSIFIER:RandomForestClassifier,
    ModelDefinition.Algorithm.LINEAR_REGRESSION:LinearRegression,
    ModelDefinition.Algorithm.RANDOM_FOREST_REGRESSOR:RandomForestRegressor,
}

def validate_algorithm_task(model):
    classification={ModelDefinition.Algorithm.LOGISTIC_REGRESSION,ModelDefinition.Algorithm.RANDOM_FOREST_CLASSIFIER}
    regression={ModelDefinition.Algorithm.LINEAR_REGRESSION,ModelDefinition.Algorithm.RANDOM_FOREST_REGRESSOR}
    if model.task_type==ModelDefinition.TaskType.CLASSIFICATION and model.algorithm not in classification:
        raise ValueError("El algoritmo no corresponde a CLASSIFICATION.")
    if model.task_type==ModelDefinition.TaskType.REGRESSION and model.algorithm not in regression:
        raise ValueError("El algoritmo no corresponde a REGRESSION.")

def build_pipeline(model,dataframe,feature_names):
    numeric=[n for n in feature_names if pd.api.types.is_numeric_dtype(dataframe[n])]
    categorical=[n for n in feature_names if n not in numeric]
    preprocessor=ColumnTransformer(
        transformers=[
            ("num",Pipeline([("imputer",SimpleImputer(strategy="median"))]),numeric),
            ("cat",Pipeline([("imputer",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),categorical),
        ],
        remainder="drop",
    )
    estimator_cls=ALGORITHM_FACTORY[model.algorithm]
    params=dict(model.parameters or {})
    try:
        probe=estimator_cls()
        if "random_state" in probe.get_params(): params.setdefault("random_state",model.random_state)
    except TypeError:
        pass
    estimator=estimator_cls(**params)
    return Pipeline([("preprocessor",preprocessor),("estimator",estimator)])

def evaluation_metrics(model,y_true,y_pred,estimator=None,X_test=None):
    if model.task_type==ModelDefinition.TaskType.CLASSIFICATION:
        labels=list(getattr(estimator,"classes_",[])) if estimator is not None else []
        average="binary" if len(labels)==2 else "weighted"
        result={
            "accuracy":float(accuracy_score(y_true,y_pred)),
            "precision":float(precision_score(y_true,y_pred,average=average,zero_division=0)),
            "recall":float(recall_score(y_true,y_pred,average=average,zero_division=0)),
            "f1_score":float(f1_score(y_true,y_pred,average=average,zero_division=0)),
            "f1_weighted":float(f1_score(y_true,y_pred,average="weighted",zero_division=0)),
            "confusion_matrix":confusion_matrix(y_true,y_pred,labels=labels or None).tolist(),
            "class_labels":[str(v) for v in labels],
            "classification_report":classification_report(y_true,y_pred,labels=labels or None,output_dict=True,zero_division=0),
        }
        if hasattr(y_true,"value_counts"):
            result["class_distribution"]={str(k):int(v) for k,v in y_true.value_counts().sort_index().items()}
        if estimator is not None and X_test is not None and hasattr(estimator,"predict_proba"):
            try:
                proba=estimator.predict_proba(X_test)
                if len(labels)==2:
                    positive=proba[:,1]
                    result["roc_auc"]=float(roc_auc_score(y_true,positive))
                    result["pr_auc"]=float(average_precision_score(y_true,positive))
                    try: result["log_loss"]=float(log_loss(y_true,proba,labels=labels or None))
                    except Exception: pass
                    fpr,tpr,_=roc_curve(y_true,positive,pos_label=labels[1] if labels else 1)
                    pc,rc,_=precision_recall_curve(y_true,positive,pos_label=labels[1] if labels else 1)
                    result["roc_curve"]=[{"x":float(x),"y":float(y)} for x,y in zip(fpr,tpr)]
                    result["precision_recall_curve"]=[{"x":float(x),"y":float(y)} for x,y in zip(rc,pc)]
                else:
                    result["roc_auc"]=float(roc_auc_score(y_true,proba,multi_class="ovr",average="weighted"))
            except Exception as exc: result["probability_warning"]=str(exc)
        return result
    mse=mean_squared_error(y_true,y_pred)
    residuals=y_true-y_pred
    return {"mae":float(mean_absolute_error(y_true,y_pred)),"mse":float(mse),"rmse":float(mse**0.5),"r2":float(r2_score(y_true,y_pred)),"actual_vs_predicted":[{"actual":float(a),"predicted":float(b)} for a,b in list(zip(y_true,y_pred))[:500]],"residuals":[float(v) for v in list(residuals)[:500]]}

@transaction.atomic
def ensure_model_data_asset(model):
    if model.data_asset: return model.data_asset
    asset=DataAsset.objects.create(
        workspace=model.workspace,data_source=model.dataset.source_table.data_source,name=model.name,
        asset_type=DataAsset.AssetType.ML_MODEL,status=DataAsset.Status.ACTIVE,
        metadata={"model_definition_id":str(model.id),"task_type":model.task_type,"algorithm":model.algorithm},
        created_by=model.created_by,
    )
    model.data_asset=asset; model.save(update_fields=["data_asset","updated_at"])
    create_dependency(
        workspace=model.workspace,upstream=model.dataset.source_table.data_asset,downstream=asset,
        dependency_type=AssetDependency.DependencyType.MODEL_INPUT,
        refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,
        metadata={"model_definition_id":str(model.id)},
    )
    return asset

def train_model(execution,model_run):
    model=model_run.model
    validate_algorithm_task(model)
    mark_running(execution)
    model_run.status=ModelRun.Status.RUNNING; model_run.started_at=timezone.now(); model_run.execution_id=execution.id
    model_run.parameters_snapshot=dict(model.parameters or {})
    model_run.save(update_fields=["status","started_at","execution_id","parameters_snapshot"])
    ensure_not_cancelled(execution)
    update_progress(execution,10,"Cargando dataset.")
    feature_names=list(model.features.values_list("name",flat=True))
    if not feature_names: raise ValueError("El modelo requiere al menos un feature.")
    if model.target.name in feature_names: raise ValueError("Target no puede estar incluido en features.")
    df=dataset_to_dataframe(model.dataset,columns=feature_names+[model.target.name]).dropna(subset=[model.target.name])
    if len(df)<5: raise ValueError("Dataset insuficiente para entrenamiento.")
    X=df[feature_names]; y=df[model.target.name]
    stratify=None
    if model.task_type==ModelDefinition.TaskType.CLASSIFICATION:
        counts=y.value_counts()
        if len(counts)>1 and counts.min()>=2: stratify=y
    X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=model.test_size,random_state=model.random_state,stratify=stratify)
    ensure_not_cancelled(execution)
    update_progress(execution,35,"Entrenando modelo.")
    emit_event(execution, "ML_TRAINING_STARTED", {"algorithm": model.algorithm, "task_type": model.task_type, "train_rows": len(X_train), "test_rows": len(X_test)}, family="ML")
    pipeline=build_pipeline(model,df,feature_names); pipeline.fit(X_train,y_train)
    ensure_not_cancelled(execution)
    update_progress(execution,70,"Evaluando modelo.")
    ensure_not_cancelled(execution)
    predictions=pipeline.predict(X_test); metrics=evaluation_metrics(model,y_test,predictions,estimator=pipeline,X_test=X_test)
    for metric_name, metric_value in metrics.items():
        if isinstance(metric_value, (int, float)):
            report_metric(execution, metric_name, metric_value, scope="evaluation")
    emit_event(execution, "ML_EVALUATION_COMPLETED", {"metrics": metrics, "test_rows": len(X_test)}, family="ML")
    model_asset=ensure_model_data_asset(model)
    source_asset=model.dataset.source_table.data_asset
    next_version=(model.versions.order_by("-version").values_list("version",flat=True).first() or 0)+1
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
        temp_model_path=Path(tmp.name)
    try:
        joblib.dump({"pipeline":pipeline,"feature_names":feature_names,"target_name":model.target.name,"task_type":model.task_type,"algorithm":model.algorithm},temp_model_path)
        artifact_uri=put_file(f"models/{model.id}/v{next_version}/model.joblib",temp_model_path,"application/octet-stream")
    finally:
        temp_model_path.unlink(missing_ok=True)
    version=ModelVersion.objects.create(
        model=model,run=model_run,version=next_version,artifact_path=artifact_uri,metrics=metrics,
        feature_names=feature_names,target_name=model.target.name,algorithm=model.algorithm,sklearn_version=sklearn.__version__,
    )
    finished=timezone.now()
    model_run.status=ModelRun.Status.SUCCESS; model_run.metrics=metrics
    model_run.input_asset_versions={str(source_asset.id):source_asset.version}
    model_run.row_count=len(df); model_run.train_row_count=len(X_train); model_run.test_row_count=len(X_test); model_run.finished_at=finished
    model_run.save()
    state=ensure_asset_state(model_asset); state.status="FRESH"; state.last_success_at=finished; state.last_error=""
    state.save(update_fields=["status","last_success_at","last_error","last_changed_at"])
    event=record_change(model_asset,"REFRESH",user=execution.requested_by,metadata={"model_run_id":str(model_run.id),"model_version_id":str(version.id),"execution_id":str(execution.id)})
    emit_event(execution, "ML_MODEL_CREATED", {"model_id": str(model.id), "model_version_id": str(version.id), "version": version.version, "algorithm": model.algorithm, "artifact_path": artifact_uri}, family="ML")
    result={"model_run_id":str(model_run.id),"model_version_id":str(version.id),"version":version.version,"metrics":metrics,"artifact_path":artifact_uri,"row_count":len(df),"train_row_count":len(X_train),"test_row_count":len(X_test),"change_event_id":str(event.id)}
    mark_success(execution,result); return result

def batch_inference(execution,model_version,dataset,requested_by=None):
    mark_running(execution); ensure_not_cancelled(execution); update_progress(execution,10,"Cargando modelo versionado.")
    with materialize(model_version.artifact_path, suffix=".joblib") as model_path:
        artifact=joblib.load(model_path)
    pipeline=artifact["pipeline"]; feature_names=artifact["feature_names"]
    df=dataset_to_dataframe(dataset,columns=feature_names)
    ensure_not_cancelled(execution)
    update_progress(execution,45,"Ejecutando inferencia batch.")
    output=df.copy(); output["prediction"]=pipeline.predict(df[feature_names])
    ensure_not_cancelled(execution)
    artifact_uri=dataframe_to_parquet_artifact(
        output,
        f"predictions/{model_version.model_id}/{execution.id}/predictions.parquet",
    )
    data_asset=DataAsset.objects.create(
        workspace=model_version.model.workspace,data_source=None,
        name=f"{model_version.model.name} predictions v{model_version.version} {str(execution.id)[:8]}",
        asset_type=DataAsset.AssetType.DATASET,status=DataAsset.Status.ACTIVE,
        metadata={"storage":"PARQUET_ARTIFACT","artifact_uri":artifact_uri,"artifact_path":artifact_uri,"prediction":True,"model_version_id":str(model_version.id),"row_count":len(output)},
        created_by=requested_by or model_version.model.created_by,
    )
    prediction_asset=PredictionAsset.objects.create(model_version=model_version,source_dataset=dataset,data_asset=data_asset,artifact_path=artifact_uri,row_count=len(output))
    create_dependency(workspace=model_version.model.workspace,upstream=model_version.model.data_asset,downstream=data_asset,dependency_type=AssetDependency.DependencyType.MODEL_INPUT,refresh_policy=AssetDependency.RefreshPolicy.MANUAL,metadata={"relation":"MODEL_PREDICTION"})
    create_dependency(workspace=model_version.model.workspace,upstream=dataset.source_table.data_asset,downstream=data_asset,dependency_type=AssetDependency.DependencyType.DATA,refresh_policy=AssetDependency.RefreshPolicy.MANUAL,metadata={"relation":"INFERENCE_DATASET"})
    event=record_change(data_asset,"REFRESH",user=requested_by,metadata={"prediction_asset_id":str(prediction_asset.id),"execution_id":str(execution.id)})
    result={"prediction_asset_id":str(prediction_asset.id),"data_asset_id":str(data_asset.id),"artifact_path":artifact_uri,"row_count":len(output),"change_event_id":str(event.id)}
    mark_success(execution,result); return result
