import json, os, subprocess, sys, tempfile
from pathlib import Path
from django.conf import settings
from data_science.data_io import save_dataframe_csv, table_to_dataframe

class PythonRuntimeError(RuntimeError): pass

def _preexec_limits(memory_limit_mb):
    if os.name == "nt": return None
    def apply():
        import resource
        memory_bytes=int(memory_limit_mb)*1024*1024
        resource.setrlimit(resource.RLIMIT_AS,(memory_bytes,memory_bytes))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    return apply

def execute_python_transformation_runtime(transformation):
    allowed_global=set(settings.PYTHON_RUNTIME_ALLOWED_PACKAGES)
    requested=set(transformation.allowed_packages or [])
    if not requested.issubset(allowed_global):
        raise PythonRuntimeError("Packages fuera de whitelist: "+", ".join(sorted(requested-allowed_global)))
    inputs={}
    with tempfile.TemporaryDirectory(prefix="bi_python_") as temp:
        temp_path=Path(temp)
        for item in transformation.inputs.select_related("asset","asset__data_source").all():
            try: table_asset=item.asset.table_definition
            except Exception as exc: raise PythonRuntimeError(f"Input {item.alias} no es tabular.") from exc
            if item.asset.data_source.mode != "MANAGED":
                raise PythonRuntimeError(f"Input {item.alias} es EXTERNAL; requiere adapter posterior.")
            df=table_to_dataframe(table_asset, limit=min(transformation.max_input_rows, settings.PYTHON_RUNTIME_MAX_ROWS))
            filename=f"input_{item.alias}.csv"
            save_dataframe_csv(df,temp_path/filename); inputs[item.alias]=filename
        (temp_path/"user_code.py").write_text(transformation.code, encoding="utf-8")
        manifest_path=temp_path/"manifest.json"
        manifest_path.write_text(json.dumps({"inputs":inputs,"allowed_packages":sorted(requested)}), encoding="utf-8")
        runner=Path(__file__).with_name("runner.py")
        env={"PYTHONIOENCODING":"utf-8","PYTHONUNBUFFERED":"1"}
        timeout=min(transformation.timeout_seconds, settings.PYTHON_RUNTIME_TIMEOUT_SECONDS)
        memory=min(transformation.memory_limit_mb, settings.PYTHON_RUNTIME_MEMORY_MB)
        try:
            completed=subprocess.run(
                [sys.executable,"-I",str(runner),str(manifest_path)],
                cwd=temp_path, env=env, capture_output=True, text=True,
                timeout=timeout, check=False, preexec_fn=_preexec_limits(memory),
            )
        except subprocess.TimeoutExpired as exc:
            raise PythonRuntimeError(f"Python runtime excedió {timeout} segundos.") from exc
        if completed.returncode != 0:
            raise PythonRuntimeError(completed.stderr.strip() or "Python runtime failed.")
        output_path=temp_path/"output.csv"
        if not output_path.exists(): raise PythonRuntimeError("No se produjo output.csv.")
        import pandas as pd
        output_df=pd.read_csv(output_path)
        return output_df, {"stdout":completed.stdout[-5000:],"stderr":completed.stderr[-5000:],"rows":len(output_df),"columns":list(output_df.columns)}
