from dataclasses import dataclass

from django.db import transaction

from connectors.registry import build_connector
from datasources.models import DataAsset, DataSource

from .models import FieldAsset, RelationAsset, TableAsset


@dataclass(slots=True)
class CatalogSyncResult:
    created_tables: int = 0
    updated_tables: int = 0
    created_fields: int = 0
    updated_fields: int = 0
    deleted_fields: int = 0
    created_relations: int = 0
    updated_relations: int = 0

    def to_dict(self):
        return {
            "created_tables": self.created_tables,
            "updated_tables": self.updated_tables,
            "created_fields": self.created_fields,
            "updated_fields": self.updated_fields,
            "deleted_fields": self.deleted_fields,
            "created_relations": self.created_relations,
            "updated_relations": self.updated_relations,
        }


def _asset_type_from_table_type(table_type: str):
    if table_type == "VIEW":
        return DataAsset.AssetType.VIEW
    return DataAsset.AssetType.TABLE


@transaction.atomic
def sync_catalog(
    data_source: DataSource,
    runtime_credentials: dict,
    schemas=None,
    include_views=True,
    created_by=None,
):
    connector = build_connector(data_source, runtime_credentials)
    discovered = connector.introspect_catalog(
        schemas=schemas,
        include_views=include_views,
    )

    result = CatalogSyncResult()
    table_lookup = {}

    for table in discovered:
        asset_type = _asset_type_from_table_type(table.table_type)
        logical_name = f"{table.schema}.{table.name}"

        data_asset, _ = DataAsset.objects.update_or_create(
            workspace=data_source.workspace,
            data_source=data_source,
            physical_schema=table.schema,
            physical_name=table.name,
            defaults={
                "name": logical_name,
                "asset_type": asset_type,
                "status": DataAsset.Status.ACTIVE,
                "created_by": created_by or data_source.created_by,
                "metadata": {
                    "catalog_origin": "external_introspection",
                    "native_object_type": table.table_type,
                },
            },
        )

        table_asset, created = TableAsset.objects.update_or_create(
            data_source=data_source,
            schema_name=table.schema,
            table_name=table.name,
            technical_name=table.name,
            defaults={
                "data_asset": data_asset,
                "object_type": (
                    TableAsset.ObjectType.VIEW
                    if table.table_type == "VIEW"
                    else TableAsset.ObjectType.TABLE
                ),
                "primary_key_columns": list(table.primary_key),
            },
        )
        if created:
            result.created_tables += 1
        else:
            result.updated_tables += 1

        table_lookup[(table.schema, table.name)] = table_asset

        seen_fields = set()
        for column in table.columns:
            seen_fields.add(column.name)
            field, field_created = FieldAsset.objects.update_or_create(
                table_asset=table_asset,
                name=column.name,
                defaults={
                    "logical_type": column.data_type,
                    "native_type": column.native_type,
                    "ordinal_position": column.ordinal_position,
                    "nullable": column.nullable,
                    "default_value": (
                        "" if column.default is None else str(column.default)
                    ),
                    "max_length": column.max_length,
                    "numeric_precision": column.numeric_precision,
                    "numeric_scale": column.numeric_scale,
                    "is_primary_key": column.name in table.primary_key,
                    "is_identity": column.is_identity,
                    "origin": FieldAsset.Origin.SOURCE,
                },
            )
            if field_created:
                result.created_fields += 1
            else:
                result.updated_fields += 1

        stale_fields = table_asset.fields.filter(origin=FieldAsset.Origin.SOURCE).exclude(name__in=seen_fields)
        result.deleted_fields += stale_fields.count()
        stale_fields.delete()

    # Relations are synchronized after all tables are known.
    for table in discovered:
        source_table = table_lookup.get((table.schema, table.name))
        if source_table is None:
            continue

        for fk in table.foreign_keys:
            target_table = table_lookup.get((fk.target_schema, fk.target_table))
            if target_table is None:
                # Target may be outside selected schemas. We intentionally
                # skip it instead of creating a partial catalog entry.
                continue

            relation, created = RelationAsset.objects.update_or_create(
                data_source=data_source,
                name=fk.name,
                source_table=source_table,
                defaults={
                    "target_table": target_table,
                    "source_columns": list(fk.source_columns),
                    "target_columns": list(fk.target_columns),
                },
            )
            if created:
                result.created_relations += 1
            else:
                result.updated_relations += 1

    return result
