import builtins, json, sys
from pathlib import Path
import pandas as pd

def main():
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    inputs = manifest["inputs"]
    output_path = root / "output.csv"
    code_path = root / "user_code.py"
    allowed_packages = set(manifest.get("allowed_packages", []))
    allowed_packages.update({"pandas","numpy","math","statistics","datetime","json"})
    original_import = builtins.__import__
    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        root_name = name.split(".")[0]
        if root_name not in allowed_packages:
            raise ImportError(f"Package '{root_name}' is not allowed.")
        return original_import(name, globals, locals, fromlist, level)
    safe_builtins = {
        "abs":abs,"all":all,"any":any,"bool":bool,"dict":dict,"enumerate":enumerate,
        "float":float,"int":int,"len":len,"list":list,"max":max,"min":min,"range":range,
        "round":round,"set":set,"sorted":sorted,"str":str,"sum":sum,"tuple":tuple,"zip":zip,
        "Exception":Exception,"ValueError":ValueError,"__import__":guarded_import,
    }
    def table(alias):
        if alias not in inputs: raise KeyError(f"Unknown input alias: {alias}")
        return pd.read_csv(root / inputs[alias])
    saved = {"done":False}
    def save_table(dataframe):
        if not isinstance(dataframe, pd.DataFrame): raise TypeError("save_table expects pandas.DataFrame")
        dataframe.to_csv(output_path, index=False); saved["done"]=True
    namespace={"__builtins__":safe_builtins,"pd":pd,"table":table,"save_table":save_table}
    # Expose each input alias as a pandas DataFrame (e.g. Table1['Resultado'] = ...).
    for alias in inputs:
        if alias.isidentifier(): namespace[alias]=table(alias)
    code=code_path.read_text(encoding="utf-8")
    exec(compile(code, str(code_path), "exec"), namespace, namespace)
    if not saved["done"]:
        # Notebook-style scripts may mutate/overwrite the input DataFrame directly.
        frames=[namespace[a] for a in inputs if a.isidentifier() and isinstance(namespace.get(a),pd.DataFrame)]
        if len(frames)==1:
            save_table(frames[0])
        else:
            raise RuntimeError("Save one DataFrame with save_table(df) when the script has multiple inputs.")
    print(json.dumps({"ok":True,"output":output_path.name}))
if __name__=="__main__": main()
