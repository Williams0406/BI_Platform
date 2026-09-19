import io
import pandas as pd
from .storage import put_bytes, get_bytes

def dataframe_to_parquet_artifact(dataframe, key):
    buffer = io.BytesIO()
    dataframe.to_parquet(buffer, index=False, engine="pyarrow")
    return put_bytes(key, buffer.getvalue(), "application/vnd.apache.parquet")

def parquet_artifact_to_dataframe(uri):
    return pd.read_parquet(io.BytesIO(get_bytes(uri)), engine="pyarrow")
