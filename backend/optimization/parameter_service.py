import io
import pandas as pd
from platform_ops.storage import get_bytes
from django.db import connection


AGGREGATIONS = {"SUM", "AVG", "MIN", "MAX", "COUNT"}

def quote(identifier):
    return connection.ops.quote_name(identifier)

def _cast(value, value_type):
    if value is None:
        return None
    if value_type == "INTEGER":
        return int(value)
    if value_type == "BOOLEAN":
        return bool(value)
    return float(value)

def _aggregate_series(series, aggregation):
    if aggregation == "SUM":
        return series.sum()
    if aggregation == "AVG":
        return series.mean()
    if aggregation == "MIN":
        return series.min()
    if aggregation == "MAX":
        return series.max()
    if aggregation == "COUNT":
        return series.count()
    raise ValueError(f"Agregación no soportada: {aggregation}")

def _resolve_from_asset(parameter):
    asset = parameter.source_asset
    aggregation = (parameter.source_aggregation or "SUM").upper()
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"Agregación no soportada: {aggregation}")

    # Physical MANAGED table
    try:
        table = asset.table_definition
    except Exception:
        table = None

    if table is not None and asset.data_source and asset.data_source.mode == "MANAGED":
        if not parameter.source_field_id:
            raise ValueError(
                f"El parámetro {parameter.name} requiere source_field para tabla MANAGED."
            )
        field_sql = quote(parameter.source_field.name)
        expr = f"COUNT({field_sql})" if aggregation == "COUNT" else f"{aggregation}({field_sql})"
        query = (
            f"SELECT {expr} "
            f"FROM {quote(table.schema_name)}.{quote(table.table_name)}"
        )
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]

    # Artifact inputs, including ML predictions and Python outputs.
    metadata = asset.metadata or {}
    storage = metadata.get("storage")
    if storage in {"CSV_ARTIFACT", "PARQUET_ARTIFACT"}:
        artifact_uri = metadata.get("artifact_uri") or metadata.get("artifact_path")
        column = parameter.source_column
        if not artifact_uri or not column:
            raise ValueError(
                f"El parámetro {parameter.name} requiere artifact_uri y source_column."
            )
        raw = get_bytes(artifact_uri)
        if storage == "PARQUET_ARTIFACT":
            df = pd.read_parquet(io.BytesIO(raw), engine="pyarrow")
        else:
            df = pd.read_csv(io.BytesIO(raw))
        if column not in df.columns:
            raise ValueError(
                f"Columna '{column}' no existe en artifact de {asset.name}."
            )
        return _aggregate_series(df[column], aggregation)

    raise ValueError(
        f"DataAsset {asset.name} no es una tabla MANAGED ni un CSV_ARTIFACT compatible."
    )

def resolve_parameters(model, scenario):
    values = {}
    input_versions = {}
    overrides = scenario.parameter_values or {}

    for parameter in model.parameters.select_related(
        "source_asset",
        "source_field",
        "source_asset__data_source",
    ).all():
        if parameter.name in overrides:
            values[parameter.name] = _cast(
                overrides[parameter.name],
                parameter.value_type,
            )
            continue

        if parameter.source_asset_id:
            asset = parameter.source_asset
            input_versions[str(asset.id)] = asset.version
            value = _resolve_from_asset(parameter)
            values[parameter.name] = _cast(value, parameter.value_type)
            continue

        if parameter.default_value is None:
            raise ValueError(f"El parámetro {parameter.name} no tiene valor.")
        values[parameter.name] = _cast(
            parameter.default_value,
            parameter.value_type,
        )

    unknown_overrides = set(overrides) - set(values)
    if unknown_overrides:
        raise ValueError(
            "Scenario contiene parámetros desconocidos: "
            + ", ".join(sorted(unknown_overrides))
        )
    return values, input_versions
