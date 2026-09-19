import pandas as pd
from django.db import connection

def quote(identifier):
    return connection.ops.quote_name(identifier)

def table_to_dataframe(table_asset, columns=None, limit=None):
    columns = columns or list(table_asset.fields.values_list("name", flat=True))
    if not columns:
        raise ValueError("La tabla no tiene campos catalogados.")
    allowed = set(table_asset.fields.values_list("name", flat=True))
    unknown = set(columns) - allowed
    if unknown:
        raise ValueError("Columnas desconocidas: " + ", ".join(sorted(unknown)))
    query = f"SELECT {', '.join(quote(c) for c in columns)} FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)}"
    params = []
    if limit:
        query += " LIMIT %s"
        params.append(int(limit))
    return pd.read_sql_query(query, connection, params=params)

def dataset_to_dataframe(dataset, columns=None):
    if not dataset.enabled:
        raise ValueError("Dataset deshabilitado.")
    return table_to_dataframe(dataset.source_table, columns=columns, limit=dataset.sample_limit)

def save_dataframe_csv(dataframe, path):
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)
    return path
