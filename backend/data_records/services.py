from dataclasses import dataclass
from typing import Any

from django.db import connection, transaction

from datasources.models import DataSource

from .exceptions import (
    RecordConflictError,
    RecordNotFoundError,
    UnsupportedRecordOperation,
)
from .validators import validate_record_payload




def emit_record_change(table_asset, change_type, record_key=""):
    """
    Register a lineage event after the transaction commits.

    Import is local to keep Data Records independent from the dependency engine
    at import time.
    """
    from django.db import transaction as django_transaction
    from dependencies.services import record_change
    from dependencies.tasks import propagate_asset_change_task

    asset = table_asset.data_asset

    def _after_commit():
        event = record_change(
            asset,
            change_type,
            record_key=record_key,
            metadata={"source": "data_records"},
        )
        propagate_asset_change_task.apply_async(
            args=[str(event.id)],
            queue="fast",
        )

    django_transaction.on_commit(_after_commit)


ALLOWED_FILTER_OPERATORS = {
    "eq": "=",
    "ne": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "contains": "ILIKE",
}


def quote(identifier: str) -> str:
    return connection.ops.quote_name(identifier)


def assert_managed_table(table_asset):
    if table_asset.data_source.mode != DataSource.Mode.MANAGED:
        raise UnsupportedRecordOperation(
            "Esta API de records de Fase 4 opera sobre tablas MANAGED. "
            "Las fuentes EXTERNAL continúan usando Connector read APIs."
        )


def public_field_map(table_asset):
    return {field.name: field for field in table_asset.fields.all()}


def build_filters(table_asset, query_params):
    field_map = public_field_map(table_asset)
    clauses = []
    values = []

    for key, raw_value in query_params.items():
        if not key.startswith("filter__"):
            continue

        parts = key.split("__")
        if len(parts) == 2:
            _, field_name = parts
            operator = "eq"
        elif len(parts) == 3:
            _, field_name, operator = parts
        else:
            continue

        if field_name not in field_map or operator not in ALLOWED_FILTER_OPERATORS:
            continue

        sql_operator = ALLOWED_FILTER_OPERATORS[operator]
        value = raw_value
        if operator == "contains":
            value = f"%{raw_value}%"

        clauses.append(f"{quote(field_name)} {sql_operator} %s")
        values.append(value)

    return clauses, values


def serialize_db_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_row(row):
    return {
        key: serialize_db_value(value)
        for key, value in row.items()
    }


def list_records(table_asset, query_params):
    assert_managed_table(table_asset)

    field_map = public_field_map(table_asset)
    visible_columns = list(field_map)
    # Imported/managed base tables have an optimistic-lock row-version column.
    # SQLTransformation outputs (especially VIEWs) do not. Selecting an invented
    # __row_version made valid derived datasets look empty in /app/data because
    # the preview request failed and the frontend intentionally collapsed it.
    version_column = table_asset.row_version_column or ""

    limit = min(max(int(query_params.get("limit", 100)), 1), 1000)
    offset = max(int(query_params.get("offset", 0)), 0)

    columns = visible_columns + ([version_column] if version_column else [])
    select_sql = ", ".join(quote(column) for column in columns)

    clauses, params = build_filters(table_asset, query_params)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    order_by = query_params.get("order_by")
    order_clause = ""
    if order_by:
        descending = order_by.startswith("-")
        field_name = order_by[1:] if descending else order_by
        if field_name in field_map:
            direction = "DESC" if descending else "ASC"
            order_clause = f" ORDER BY {quote(field_name)} {direction}"

    query = (
        f"SELECT {select_sql} "
        f"FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)}"
        f"{where}{order_clause} LIMIT %s OFFSET %s"
    )
    params.extend([limit, offset])

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        names = [column[0] for column in cursor.description]
        rows = [dict(zip(names, row)) for row in cursor.fetchall()]

    return {
        "rows": [serialize_row(row) for row in rows],
        "limit": limit,
        "offset": offset,
        "returned": len(rows),
    }


@transaction.atomic
def create_record(table_asset, payload):
    assert_managed_table(table_asset)
    clean = validate_record_payload(table_asset, payload, partial=False)

    if not clean:
        query = (
            f"INSERT INTO {quote(table_asset.schema_name)}."
            f"{quote(table_asset.table_name)} DEFAULT VALUES RETURNING *"
        )
        params = []
    else:
        columns = list(clean)
        placeholders = ", ".join(["%s"] * len(columns))
        query = (
            f"INSERT INTO {quote(table_asset.schema_name)}."
            f"{quote(table_asset.table_name)} "
            f"({', '.join(quote(c) for c in columns)}) "
            f"VALUES ({placeholders}) RETURNING *"
        )
        params = [clean[column] for column in columns]

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        names = [column[0] for column in cursor.description]
        row = dict(zip(names, cursor.fetchone()))

    serialized = serialize_row(row)
    pk_columns = list(table_asset.primary_key_columns or [])
    record_key = serialized.get(pk_columns[0], "") if len(pk_columns) == 1 else ""
    emit_record_change(table_asset, "INSERT", record_key)
    return serialized


def _single_pk(table_asset):
    pk = list(table_asset.primary_key_columns or [])
    if len(pk) != 1:
        raise UnsupportedRecordOperation(
            "Las operaciones por registro requieren una PK simple en Fase 4."
        )
    return pk[0]


def get_record(table_asset, record_key):
    assert_managed_table(table_asset)
    pk = _single_pk(table_asset)

    query = (
        f"SELECT * FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
        f"WHERE {quote(pk)} = %s"
    )

    with connection.cursor() as cursor:
        cursor.execute(query, [record_key])
        row = cursor.fetchone()
        if row is None:
            raise RecordNotFoundError("Registro no encontrado.")
        names = [column[0] for column in cursor.description]
        return serialize_row(dict(zip(names, row)))


@transaction.atomic
def update_record(table_asset, record_key, payload, expected_version):
    assert_managed_table(table_asset)
    pk = _single_pk(table_asset)
    version_column = table_asset.row_version_column or "__row_version"

    clean = validate_record_payload(table_asset, payload, partial=True)
    clean.pop(pk, None)

    if not clean:
        return get_record(table_asset, record_key)

    assignments = [f"{quote(name)} = %s" for name in clean]
    assignments.append(f"{quote(version_column)} = {quote(version_column)} + 1")

    params = [clean[name] for name in clean]
    params.extend([record_key, int(expected_version)])

    query = (
        f"UPDATE {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
        f"SET {', '.join(assignments)} "
        f"WHERE {quote(pk)} = %s AND {quote(version_column)} = %s "
        f"RETURNING *"
    )

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                f"SELECT {quote(version_column)} "
                f"FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
                f"WHERE {quote(pk)} = %s",
                [record_key],
            )
            exists = cursor.fetchone()
            if exists is None:
                raise RecordNotFoundError("Registro no encontrado.")
            raise RecordConflictError(
                "El registro fue modificado por otro proceso. Recargue y vuelva a intentar."
            )

        names = [column[0] for column in cursor.description]
        serialized = serialize_row(dict(zip(names, row)))
        emit_record_change(table_asset, "UPDATE", record_key)
        return serialized


@transaction.atomic
def delete_record(table_asset, record_key, expected_version):
    assert_managed_table(table_asset)
    pk = _single_pk(table_asset)
    version_column = table_asset.row_version_column or "__row_version"

    query = (
        f"DELETE FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
        f"WHERE {quote(pk)} = %s AND {quote(version_column)} = %s "
        f"RETURNING {quote(pk)}"
    )

    with connection.cursor() as cursor:
        cursor.execute(query, [record_key, int(expected_version)])
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                f"SELECT {quote(version_column)} "
                f"FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
                f"WHERE {quote(pk)} = %s",
                [record_key],
            )
            exists = cursor.fetchone()
            if exists is None:
                raise RecordNotFoundError("Registro no encontrado.")
            raise RecordConflictError(
                "El registro cambió desde que fue cargado. Recargue antes de eliminarlo."
            )

    emit_record_change(table_asset, "DELETE", record_key)
    return {"deleted": True, "primary_key": record_key}
