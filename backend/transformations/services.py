import hashlib

from django.db import connection, transaction
from django.utils import timezone

from data_model.models import FieldAsset, TableAsset
from data_model.managed_services import ensure_managed_datasource, workspace_schema_name
from datasources.models import DataAsset
from dependencies.models import AssetDependency, AssetState
from dependencies.services import create_dependency, ensure_asset_state, record_change
from execution.models import Execution
from execution.services import append_log, mark_failed, mark_running, mark_success, update_progress

from .models import SQLTransformation, TransformationInput
from .sql_validation import resolve_asset_tokens, validate_select_sql


def quote(identifier):
    return connection.ops.quote_name(identifier)


def output_physical_name(transformation):
    digest = hashlib.sha1(str(transformation.id).encode()).hexdigest()[:10]
    return f"tr_{digest}"


def infer_columns(schema_name, table_name):
    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            ordinal_position,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [schema_name, table_name])
        return cursor.fetchall()


TYPE_MAP = {
    "smallint": "INTEGER",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "numeric": "DECIMAL",
    "decimal": "DECIMAL",
    "real": "FLOAT",
    "double precision": "FLOAT",
    "boolean": "BOOLEAN",
    "character varying": "STRING",
    "character": "STRING",
    "text": "TEXT",
    "date": "DATE",
    "timestamp without time zone": "DATETIME",
    "timestamp with time zone": "DATETIME_TZ",
    "time without time zone": "TIME",
    "uuid": "UUID",
    "json": "JSON",
    "jsonb": "JSON",
    "bytea": "BINARY",
}


@transaction.atomic
def sync_transformation_metadata(transformation, used_assets):
    TransformationInput.objects.filter(transformation=transformation).delete()
    for asset in used_assets:
        TransformationInput.objects.get_or_create(
            transformation=transformation,
            asset=asset,
        )

    if transformation.output_asset:
        for asset in used_assets:
            create_dependency(
                workspace=transformation.workspace,
                upstream=asset,
                downstream=transformation.output_asset,
                dependency_type=AssetDependency.DependencyType.CALCULATION,
                refresh_policy=(
                    AssetDependency.RefreshPolicy.AUTO
                    if transformation.refresh_policy == SQLTransformation.RefreshPolicy.AUTO
                    else AssetDependency.RefreshPolicy.MARK_STALE
                ),
                metadata={
                    "producer_type": "SQL_TRANSFORMATION",
                    "producer_id": str(transformation.id),
                },
            )


def execute_sql_transformation(execution):
    transformation = SQLTransformation.objects.select_related(
        "workspace",
        "created_by",
        "output_asset",
    ).get(id=execution.object_id)

    if not transformation.enabled:
        raise ValueError("La transformación está deshabilitada.")

    mark_running(execution)
    update_progress(execution, 10, "Validando SQL.")

    sql_text = validate_select_sql(transformation.sql)
    rendered_sql, used_assets = resolve_asset_tokens(
        sql_text,
        transformation.workspace,
    )

    update_progress(execution, 25, "Dependencias resueltas.")

    source = ensure_managed_datasource(
        transformation.workspace,
        transformation.created_by,
    )
    schema_name = workspace_schema_name(transformation.workspace_id)
    physical_name = output_physical_name(transformation)

    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {quote(schema_name)}")

        if transformation.output_mode == SQLTransformation.OutputMode.VIEW:
            cursor.execute(
                f"DROP VIEW IF EXISTS {quote(schema_name)}.{quote(physical_name)} CASCADE"
            )
            cursor.execute(
                f"DROP TABLE IF EXISTS {quote(schema_name)}.{quote(physical_name)} CASCADE"
            )
            cursor.execute(
                f"CREATE VIEW {quote(schema_name)}.{quote(physical_name)} AS {rendered_sql}"
            )
            asset_type = DataAsset.AssetType.VIEW
            object_type = TableAsset.ObjectType.VIEW
        else:
            cursor.execute(
                f"DROP VIEW IF EXISTS {quote(schema_name)}.{quote(physical_name)} CASCADE"
            )
            cursor.execute(
                f"DROP TABLE IF EXISTS {quote(schema_name)}.{quote(physical_name)} CASCADE"
            )
            cursor.execute(
                f"CREATE TABLE {quote(schema_name)}.{quote(physical_name)} AS {rendered_sql}"
            )
            asset_type = DataAsset.AssetType.DERIVED_TABLE
            object_type = TableAsset.ObjectType.TABLE

    update_progress(execution, 65, "Resultado SQL materializado.")

    asset = transformation.output_asset
    if asset is None:
        asset = DataAsset.objects.create(
            workspace=transformation.workspace,
            data_source=source,
            name=transformation.name,
            asset_type=asset_type,
            status=DataAsset.Status.ACTIVE,
            physical_schema=schema_name,
            physical_name=physical_name,
            metadata={
                "producer": "SQL_TRANSFORMATION",
                "producer_id": str(transformation.id),
            },
            created_by=transformation.created_by,
        )
        transformation.output_asset = asset
        transformation.save(update_fields=["output_asset", "updated_at"])
    else:
        asset.data_source = source
        asset.asset_type = asset_type
        asset.status = DataAsset.Status.ACTIVE
        asset.physical_schema = schema_name
        asset.physical_name = physical_name
        asset.metadata = {
            **(asset.metadata or {}),
            "producer": "SQL_TRANSFORMATION",
            "producer_id": str(transformation.id),
        }
        asset.save()

    table_asset, _ = TableAsset.objects.update_or_create(
        data_asset=asset,
        defaults={
            "data_source": source,
            "schema_name": schema_name,
            "table_name": physical_name,
            "object_type": object_type,
            "primary_key_columns": [],
            "row_version_column": "",
        },
    )

    columns = infer_columns(schema_name, physical_name)
    seen = []
    for row in columns:
        name, native_type, is_nullable, ordinal, max_length, precision, scale = row
        seen.append(name)
        FieldAsset.objects.update_or_create(
            table_asset=table_asset,
            name=name,
            defaults={
                "logical_type": TYPE_MAP.get(native_type, "OTHER"),
                "native_type": native_type,
                "ordinal_position": ordinal,
                "nullable": is_nullable == "YES",
                "max_length": max_length,
                "numeric_precision": precision,
                "numeric_scale": scale,
                "is_primary_key": False,
                "is_identity": False,
            },
        )

    table_asset.fields.exclude(name__in=seen).delete()

    sync_transformation_metadata(transformation, used_assets)

    state = ensure_asset_state(asset)
    state.status = AssetState.Status.FRESH
    state.last_success_at = timezone.now()
    state.last_error = ""
    state.save(
        update_fields=[
            "status",
            "last_success_at",
            "last_error",
            "last_changed_at",
        ]
    )

    event = record_change(
        asset,
        "REFRESH",
        user=execution.requested_by,
        metadata={
            "transformation_id": str(transformation.id),
            "execution_id": str(execution.id),
        },
    )

    update_progress(execution, 90, "Catálogo y lineage actualizados.")

    result = {
        "transformation_id": str(transformation.id),
        "output_asset_id": str(asset.id),
        "schema": schema_name,
        "physical_name": physical_name,
        "output_mode": transformation.output_mode,
        "input_assets": [str(asset.id) for asset in used_assets],
        "change_event_id": str(event.id),
    }

    mark_success(execution, result)
    return result
