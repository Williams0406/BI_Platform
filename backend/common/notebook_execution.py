import ast
import base64
import json
import re
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import connection

from data_model.models import TableAsset
from data_science.data_io import table_to_dataframe
from .environment_services import ensure_environment
from .models import PythonEnvironment, EnvironmentPackage, ScriptBlock
from .script_publish import _find_table, _qualify_source, _quote_source_fields

MAX_PREVIEW_ROWS = 40
MAX_INPUT_ROWS = settings.PYTHON_RUNTIME_MAX_ROWS
IMPORT_PACKAGE_ALIASES = {"sklearn": "scikit-learn", "PIL": "pillow", "cv2": "opencv-python", "yaml": "pyyaml"}


def _records(df, limit=MAX_PREVIEW_ROWS):
    preview = df.head(limit).copy().where(pd.notnull(df.head(limit)), None)
    return {"kind":"table","columns":[str(c) for c in preview.columns],"rows":preview.to_dict(orient="records"),"row_count":int(len(df)),"truncated":len(df)>limit}


def execute_sql(block):
    sql=(block.code or "").strip().rstrip(";")
    if not re.match(r"^\s*(SELECT|WITH)\b",sql,re.I): return {"kind":"text","text":"SQL saved. Preview is available for SELECT/WITH queries."}
    table=_find_table(block.workspace,sql)
    if not table: raise ValueError("No se encontró la tabla usada por el SQL en este workspace.")
    rendered=_quote_source_fields(_qualify_source(sql,table),table)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM ({rendered}) AS notebook_preview LIMIT %s",[MAX_PREVIEW_ROWS])
        columns=[col[0] for col in cursor.description]; values=cursor.fetchall()
    rows=[dict(zip(columns,row)) for row in values]
    return {"kind":"table","columns":columns,"rows":rows,"row_count":len(rows),"truncated":len(rows)>=MAX_PREVIEW_ROWS}


def _python_tables_for_code(workspace, code):
    qs=(TableAsset.objects.filter(data_source__workspace=workspace).select_related("data_asset","data_source").prefetch_related("fields"))
    found=[]; seen=set()
    for table in qs:
        names=[table.technical_name,table.table_name,getattr(table.data_asset,"name",""),getattr(table.data_asset,"physical_name","")]
        alias=next((n for n in names if n and str(n).isidentifier() and re.search(rf"(?<![A-Za-z0-9_]){re.escape(str(n))}(?![A-Za-z0-9_])",code)),None)
        if alias and table.id not in seen: found.append((alias,table)); seen.add(table.id)
    return found


def _imports(code):
    try: tree=ast.parse(code)
    except SyntaxError: return []
    roots=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): roots.extend(a.name.split(".")[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module: roots.append(node.module.split(".")[0])
    return sorted(set(roots))


def _resolve_environment(block, environment_id=None):
    # A workspace owns exactly one Python runtime.  environment_id is accepted
    # for backwards API compatibility but deliberately ignored so Scripts,
    # Data Science and Optimization cannot drift onto different runtimes.
    env=(PythonEnvironment.objects.filter(workspace=block.workspace)
         .prefetch_related("packages").first())
    if not env:
        raise ValueError("No Python environment exists for this workspace. Open Platform Settings → Python environments to create it.")
    return env


def _queue_package_install(env, package_name):
    """Ensure a package has an EnvironmentPackage row and queue installation.

    This intentionally does not treat packages installed in Django's own venv as
    installed in a Code environment: every PythonEnvironment owns its isolated venv.
    """
    from .environment_tasks import install_environment_package
    package, _ = EnvironmentPackage.objects.get_or_create(
        environment=env,
        name=package_name,
        defaults={"version_spec":"", "status":"REQUESTED", "source":"PYPI"},
    )
    if package.status != "INSTALLING":
        package.status="REQUESTED"
        package.log=""
        package.save(update_fields=["status","log","updated_at"])
        install_environment_package.apply_async(args=[str(package.id)], queue="python")
    return package


def _require_environment_package(env, package_name, import_name=None):
    import_name=import_name or package_name
    package=env.packages.filter(name__iexact=package_name).first()
    if package and package.status == "INSTALLED":
        return package
    package=_queue_package_install(env, package_name)
    state=package.status
    raise ValueError(
        f"Environment error: {package_name} is not installed in {env.name} · v{env.version}. "
        f"Installation has been queued on the python worker (current state: {state}). "
        "Wait until the package shows INSTALLED, then run the block again."
    )


def _validate_imports(env, code):
    requested=_imports(code)
    installed={p.name.lower():p for p in env.packages.all() if p.status=="INSTALLED"}
    missing=[]
    for root in requested:
        package=IMPORT_PACKAGE_ALIASES.get(root,root).lower()
        if package in installed: continue
        missing.append((root,package))
    # Stdlib modules are valid without an EnvironmentPackage row. Probe using
    # the isolated interpreter belonging to the selected environment.
    if missing:
        py=ensure_environment(env)
        roots=[root for root,_ in missing]
        probe="import importlib.util,json,sys; print(json.dumps({x:bool(importlib.util.find_spec(x)) for x in sys.argv[1:]}))"
        result=subprocess.run([str(py),"-c",probe,*roots],capture_output=True,text=True,timeout=15)
        resolved=json.loads(result.stdout.strip() or "{}") if result.returncode==0 else {}
        missing=[(root,pkg) for root,pkg in missing if not resolved.get(root)]
    if missing:
        # Queue the first missing dependency. Subsequent runs will progressively
        # reconcile the environment without ever installing into Django's venv.
        root,package=missing[0]
        _require_environment_package(env,package,root)



def _assigned_names(code):
    """Return simple variable names assigned by the current cell."""
    try:
        tree=ast.parse(code or "")
    except SyntaxError:
        return []
    names=[]
    def add_target(target):
        if isinstance(target,ast.Name): names.append(target.id)
        elif isinstance(target,(ast.Tuple,ast.List)):
            for item in target.elts: add_target(item)
    for node in tree.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign,ast.NamedExpr)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            for target in targets: add_target(target)
    return list(dict.fromkeys(names))


def _table_cache_file(table):
    """Cache a workspace table snapshot so notebook cells do not re-query and
    re-serialize hundreds of thousands of rows on every execution."""
    root=Path(settings.BASE_DIR)/".runtime_cache"/"notebook_tables"
    root.mkdir(parents=True,exist_ok=True)
    stamp=getattr(table,"last_synced_at",None)
    fields="|".join(f"{f.name}:{f.logical_type}" for f in table.fields.all())
    fingerprint=hashlib.sha1(f"{table.id}|{stamp}|{fields}|{MAX_INPUT_ROWS}".encode()).hexdigest()[:16]
    return root/f"{table.id}-{fingerprint}.pkl"


def _materialize_table_input(table):
    cache=_table_cache_file(table)
    if cache.exists():
        return cache
    df=table_to_dataframe(table,limit=(MAX_INPUT_ROWS + 1 if MAX_INPUT_ROWS else None))
    if MAX_INPUT_ROWS and len(df)>MAX_INPUT_ROWS:
        raise ValueError(f"Python runtime input limit exceeded for {table.technical_name or table.table_name}: more than {MAX_INPUT_ROWS:,} rows. Increase PYTHON_RUNTIME_MAX_ROWS deliberately or work with a sampled/derived table.")
    tmp=cache.with_suffix(".tmp")
    df.to_pickle(tmp)
    tmp.replace(cache)
    # Keep only the newest snapshots for this table.
    siblings=sorted(cache.parent.glob(f"{table.id}-*.pkl"),key=lambda x:x.stat().st_mtime,reverse=True)
    for old in siblings[3:]:
        try: old.unlink()
        except OSError: pass
    return cache

def _session_blocks(block):
    rows=list(ScriptBlock.objects.filter(workspace=block.workspace,language="PYTHON").order_by("created_at"))
    rows.sort(key=lambda x:((x.context or {}).get("notebook_order",10**9),str(x.created_at)))
    pos=next((i for i,x in enumerate(rows) if x.id==block.id),len(rows)-1)
    return rows[:pos+1]


def execute_python(block, environment_id=None, capture_variable=None):
    env=_resolve_environment(block,environment_id)
    blocks=_session_blocks(block)
    codes=[b.code or "" for b in blocks]
    all_code="\n".join(codes)
    _validate_imports(env,all_code)
    # Workspace tables are materialized as DataFrames in the isolated runtime,
    # so pandas is a runtime dependency even when the user did not type an
    # explicit `import pandas`. Queue it automatically if needed.
    table_inputs=_python_tables_for_code(block.workspace,all_code)
    if table_inputs:
        _require_environment_package(env,"pandas","pandas")
    py=ensure_environment(env)
    with tempfile.TemporaryDirectory(prefix="bi_notebook_") as tmp:
        root=Path(tmp); inputs={}
        for alias,table in table_inputs:
            cached=_materialize_table_input(table)
            filename=f"{alias}.pkl"
            try:
                # Hard links avoid copying large snapshots on the same volume.
                (root/filename).hardlink_to(cached)
            except OSError:
                shutil.copy2(cached,root/filename)
            inputs[alias]=filename
        payload={"inputs":inputs,"codes":codes,"max_rows":MAX_PREVIEW_ROWS,"capture_variable":capture_variable,"assigned_names":_assigned_names(block.code or "")}
        (root/"payload.json").write_text(json.dumps(payload),encoding="utf-8")
        from pathlib import Path as _Path
        api_source=_Path(__file__).resolve().parents[1]/"optimization"/"code_api.py"
        (root/"bi_optimization.py").write_text(api_source.read_text(encoding="utf-8"),encoding="utf-8")
        runner=r'''
import ast,contextlib,io,json,sys,traceback,base64
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); root=Path(sys.argv[1]).parent
try:
 import pandas as pd
except Exception:
 pd=None
if p["inputs"] and pd is None:
 print("__BI_ERROR__pandas is required in this Python environment to use workspace tables."); raise SystemExit(2)
ns={"pd":pd} if pd is not None else {}
# Expose the platform optimization DSL even in Python isolated mode (-I).
import types
_bi_opt=types.ModuleType("bi_optimization")
exec((root/"bi_optimization.py").read_text(encoding="utf-8"),_bi_opt.__dict__)
sys.modules["bi_optimization"]=_bi_opt
ns["optimization"]=_bi_opt
for alias,file in p["inputs"].items(): ns[alias]=pd.read_pickle(root/file)
last_value=None; final_stdout=""
try:
 for idx,code in enumerate(p["codes"]):
  tree=ast.parse(code,mode="exec"); last=None
  if idx==len(p["codes"])-1 and tree.body and isinstance(tree.body[-1],ast.Expr): last=tree.body.pop()
  out=io.StringIO()
  with contextlib.redirect_stdout(out):
   if tree.body: exec(compile(tree,"<notebook>","exec"),ns,ns)
   if last: last_value=eval(compile(ast.Expression(last.value),"<notebook>","eval"),ns,ns)
  if idx==len(p["codes"])-1: final_stdout=out.getvalue()
 # Discover publishable variables after the complete notebook session.
 variables=[]
 for name,obj in ns.items():
  if name.startswith("_") or name in {"pd"}: continue
  if pd is not None and isinstance(obj,pd.DataFrame): variables.append({"name":name,"kind":"dataframe","rows":len(obj),"columns":[str(c) for c in obj.columns]})
  elif isinstance(obj,(int,float,bool)) and not isinstance(obj,complex): variables.append({"name":name,"kind":"scalar","value":obj})
  elif hasattr(obj,"_bi_optimization_spec"):
   try: variables.append({"name":name,"kind":"optimization_model","model_name":obj.name,"problem_type":obj.problem_type,"solve_requested":bool(obj._solve_requested),"variables_count":len(obj._variables),"constraints_count":len(obj._constraints)})
   except Exception as opt_exc: variables.append({"name":name,"kind":"optimization_model","error":str(opt_exc)})
  elif hasattr(obj,"fit") and hasattr(obj,"predict") and obj.__class__.__module__.split(".")[0] in {"sklearn","xgboost","lightgbm","catboost"}:
   variables.append({"name":name,"kind":"ml_model","class_name":obj.__class__.__name__,"module":obj.__class__.__module__})
 created=[v for v in variables if v.get("name") in set(p.get("assigned_names") or [])]
 # Persist DataFrames assigned by this cell once, so the Django side can publish
 # them without executing the whole notebook a second time.
 auto_captures=[]
 if pd is not None:
  for item in created:
   if item.get("kind")!="dataframe": continue
   name=item.get("name"); target=ns.get(name)
   if isinstance(target,pd.DataFrame):
    filename="auto_"+str(len(auto_captures))+".pkl"; target.to_pickle(root/filename); auto_captures.append({"name":name,"file":filename})
 (root/"auto_captures.json").write_text(json.dumps(auto_captures))
 result={"kind":"text","text":final_stdout or "Execution completed.","variables":variables,"created_variables":created}
 if p.get("capture_variable"):
  target=ns.get(p["capture_variable"])
  if pd is not None and isinstance(target,pd.DataFrame):
   target.to_csv(root/"captured.csv",index=False); (root/"captured.json").write_text(json.dumps({"kind":"dataframe","name":p["capture_variable"]}))
  elif isinstance(target,(int,float,bool)) and not isinstance(target,complex):
   (root/"captured.json").write_text(json.dumps({"kind":"scalar","name":p["capture_variable"],"value":target}))
  elif hasattr(target,"_bi_optimization_spec"):
   spec=target._bi_optimization_spec
   (root/"captured.json").write_text(json.dumps({"kind":"optimization_model","name":p["capture_variable"],"spec":spec},default=str))
  elif hasattr(target,"fit") and hasattr(target,"predict"):
   import joblib
   joblib.dump(target,root/"captured_model.joblib")
   meta={"kind":"ml_model","name":p["capture_variable"],"class_name":target.__class__.__name__,"module":target.__class__.__module__}
   # Infer feature/target metadata from conventional train/test variables when available.
   for xn in ("X_train","X","x_train","x"):
    x=ns.get(xn)
    if pd is not None and isinstance(x,pd.DataFrame): meta["feature_names"]=[str(c) for c in x.columns]; break
   for yn in ("y_train","y","Y_train","Y"):
    y=ns.get(yn)
    if pd is not None and isinstance(y,pd.Series): meta["target_name"]=str(y.name or "target"); break
   # Evaluate against conventional train/test variables when possible.
   xtrain=ns.get("X_train"); xt=ns.get("X_test"); yt=ns.get("y_test")
   if xtrain is not None:
    try: meta["train_row_count"]=len(xtrain)
    except Exception: pass
   if pd is not None and isinstance(xt,pd.DataFrame) and yt is not None:
    try:
     pred=target.predict(xt); meta["test_row_count"]=len(xt)
     try:
      from sklearn.base import is_classifier
      classifier=bool(is_classifier(target))
     except Exception: classifier="Classifier" in target.__class__.__name__
     meta["task_type"]="CLASSIFICATION" if classifier else "REGRESSION"
     if classifier:
      from sklearn.metrics import (accuracy_score,f1_score,precision_score,recall_score,confusion_matrix,classification_report,roc_auc_score,roc_curve,precision_recall_curve,average_precision_score,log_loss)
      labels=list(getattr(target,"classes_",[]))
      avg="binary" if len(labels)==2 else "weighted"
      metrics={
       "accuracy":float(accuracy_score(yt,pred)),
       "precision":float(precision_score(yt,pred,average=avg,zero_division=0)),
       "recall":float(recall_score(yt,pred,average=avg,zero_division=0)),
       "f1_score":float(f1_score(yt,pred,average=avg,zero_division=0)),
       "precision_weighted":float(precision_score(yt,pred,average="weighted",zero_division=0)),
       "recall_weighted":float(recall_score(yt,pred,average="weighted",zero_division=0)),
       "f1_weighted":float(f1_score(yt,pred,average="weighted",zero_division=0)),
      }
      meta["confusion_matrix"]=confusion_matrix(yt,pred,labels=labels or None).tolist()
      meta["class_labels"]=[str(v) for v in labels]
      meta["classification_report"]=classification_report(yt,pred,labels=labels or None,output_dict=True,zero_division=0)
      meta["class_distribution"]={str(k):int(v) for k,v in yt.value_counts().sort_index().items()} if hasattr(yt,"value_counts") else {}
      try:
       proba=target.predict_proba(xt)
       if len(labels)==2:
        positive=proba[:,1]
        metrics["roc_auc"]=float(roc_auc_score(yt,positive))
        metrics["pr_auc"]=float(average_precision_score(yt,positive))
        try: metrics["log_loss"]=float(log_loss(yt,proba,labels=labels or None))
        except Exception: pass
        fpr,tpr,_=roc_curve(yt,positive,pos_label=labels[1] if labels else 1)
        precision_curve,recall_curve,_=precision_recall_curve(yt,positive,pos_label=labels[1] if labels else 1)
        meta["roc_curve"]=[{"x":float(x),"y":float(y)} for x,y in zip(fpr,tpr)]
        meta["precision_recall_curve"]=[{"x":float(x),"y":float(y)} for x,y in zip(recall_curve,precision_curve)]
        hist,bins=__import__("numpy").histogram(positive,bins=12,range=(0,1))
        meta["probability_distribution"]=[{"x":float((bins[i]+bins[i+1])/2),"y":int(hist[i])} for i in range(len(hist))]
       else:
        metrics["roc_auc"]=float(roc_auc_score(yt,proba,multi_class="ovr",average="weighted"))
        try: metrics["log_loss"]=float(log_loss(yt,proba,labels=labels or None))
        except Exception: pass
      except Exception as probability_exc:
       meta["probability_warning"]=str(probability_exc)
      meta["metrics"]=metrics
     else:
      from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
      mse=mean_squared_error(yt,pred); meta["metrics"]={"mae":float(mean_absolute_error(yt,pred)),"mse":float(mse),"rmse":float(mse**0.5),"r2":float(r2_score(yt,pred))}
    except Exception as eval_exc: meta["evaluation_warning"]=str(eval_exc)
   try:
    vals=getattr(target,"feature_importances_",None)
    if vals is not None: meta["feature_importance"]=[float(v) for v in vals]
   except Exception: pass
   (root/"captured.json").write_text(json.dumps(meta,default=str))
  else: raise ValueError("Variable is not a publishable DataFrame, numeric scalar, trained ML estimator, or optimization model.")
 value=last_value
 if pd is not None and isinstance(value,pd.DataFrame):
  d=value.head(p["max_rows"]); result={"kind":"table","columns":[str(c) for c in d.columns],"rows":json.loads(d.to_json(orient="records",date_format="iso")),"row_count":len(value),"truncated":len(value)>len(d),"stdout":final_stdout,"variables":variables,"created_variables":created}
 elif pd is not None and isinstance(value,pd.Series):
  d=value.head(p["max_rows"]).reset_index(); result={"kind":"table","columns":[str(c) for c in d.columns],"rows":json.loads(d.to_json(orient="records",date_format="iso")),"row_count":len(value),"truncated":len(value)>len(d),"stdout":final_stdout,"variables":variables,"created_variables":created}
 elif value is not None: result={"kind":"text","text":final_stdout+("\n" if final_stdout else "")+repr(value),"variables":variables,"created_variables":created}
 else:
  try:
   import matplotlib.pyplot as plt
   if plt.get_fignums():
    fig=plt.gcf(); buf=io.BytesIO(); fig.savefig(buf,format="png",bbox_inches="tight",dpi=130); plt.close("all")
    result={"kind":"image","mime_type":"image/png","data":base64.b64encode(buf.getvalue()).decode(),"stdout":final_stdout,"variables":variables,"created_variables":created}
  except Exception: pass
 print("__BI_RESULT__"+json.dumps(result,default=str))
except Exception as e:
 print("__BI_ERROR__"+"".join(traceback.format_exception_only(type(e),e)).strip())
 raise SystemExit(1)
'''
        runner_path=root/"runner.py"; runner_path.write_text(runner,encoding="utf-8")
        try: completed=subprocess.run([str(py),"-I",str(runner_path),str(root/"payload.json")],cwd=root,capture_output=True,text=True,timeout=settings.PYTHON_RUNTIME_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc: raise ValueError("Python execution exceeded 60 seconds.") from exc
        error=next((x[len("__BI_ERROR__"):] for x in completed.stdout.splitlines() if x.startswith("__BI_ERROR__")),None)
        if completed.returncode!=0: raise ValueError(error or (completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "Python execution failed."))
        marker=next((x[len("__BI_RESULT__"):] for x in completed.stdout.splitlines() if x.startswith("__BI_RESULT__")),None)
        output=json.loads(marker) if marker else {"kind":"text","text":"Execution completed."}
        output["environment"]={"id":str(env.id),"name":env.name,"version":env.version,"python_version":env.python_version}
        auto_meta=root/"auto_captures.json"
        if auto_meta.exists():
            captures={}
            for item in json.loads(auto_meta.read_text(encoding="utf-8") or "[]"):
                path=root/item["file"]
                if path.exists(): captures[item["name"]]=pd.read_pickle(path)
            if captures: output["_captured_dataframes"]=captures
        if capture_variable:
            capture_meta=root/"captured.json"
            if not capture_meta.exists(): raise ValueError("The requested variable was not captured.")
            captured=json.loads(capture_meta.read_text(encoding="utf-8"))
            if captured["kind"]=="dataframe": captured["dataframe"]=pd.read_csv(root/"captured.csv")
            elif captured["kind"]=="ml_model":
                import base64
                captured["artifact_base64"]=base64.b64encode((root/"captured_model.joblib").read_bytes()).decode("ascii")
            return captured
        return output


def execute_block(block, environment_id=None):
    language=(block.language or "").upper()
    if language=="PYTHON": return execute_python(block,environment_id)
    if language=="SQL": return execute_sql(block)
    return {"kind":"text","text":"DAX block validated and saved. Measure publication is shown in Data."}
