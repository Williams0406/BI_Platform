import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(sys.argv[1]).parent
    df = pd.read_csv(root / "input.csv")
    code = (root / "measure.py").read_text(encoding="utf-8")
    dimensions = manifest.get("dimensions", [])

    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "Exception": Exception,
        "ValueError": ValueError,
    }
    namespace = {"__builtins__": safe_builtins, "pd": pd, "np": np}
    exec(compile(code, "measure.py", "exec"), namespace, namespace)
    fn = namespace.get("measure")
    if not callable(fn):
        raise RuntimeError("Python measures must define: def measure(df): ...")

    rows = []
    if dimensions:
        key = dimensions[0] if len(dimensions) == 1 else dimensions
        grouped = df.groupby(key, dropna=False, sort=True)
        for group_key, group in grouped:
            values = group_key if isinstance(group_key, tuple) else (group_key,)
            row = {
                name: (None if pd.isna(value) else value)
                for name, value in zip(dimensions, values)
            }
            value = fn(group.copy())
            if hasattr(value, "item"):
                value = value.item()
            row["value"] = None if pd.isna(value) else value
            rows.append(row)
    else:
        value = fn(df.copy())
        if hasattr(value, "item"):
            value = value.item()
        rows.append({"value": None if pd.isna(value) else value})

    pd.DataFrame(rows).to_csv(root / "output.csv", index=False)


if __name__ == "__main__":
    main()
