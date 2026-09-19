from django.db import transaction

from data_model.models import FieldAsset, RelationAsset, TableAsset
from datasources.models import DataAsset


@transaction.atomic
def sync_gateway_catalog(data_source, catalog, created_by=None):
    result = {
        "created_tables": 0,
        "updated_tables": 0,
        "created_fields": 0,
        "updated_fields": 0,
        "deleted_fields": 0,
        "created_relations": 0,
        "updated_relations": 0,
    }
    lookup = {}
    catalog = catalog or []

    for table in catalog:
        schema = table["schema"]
        name = table["name"]
        table_type = table.get("table_type", "TABLE")
        asset_type = (
            DataAsset.AssetType.VIEW
            if table_type == "VIEW"
            else DataAsset.AssetType.TABLE
        )
        logical_name = f"{schema}.{name}"

        asset, _ = DataAsset.objects.update_or_create(
            workspace=data_source.workspace,
            data_source=data_source,
            physical_schema=schema,
            physical_name=name,
            defaults={
                "name": logical_name,
                "asset_type": asset_type,
                "status": DataAsset.Status.ACTIVE,
                "created_by": created_by or data_source.created_by,
                "metadata": {
                    "catalog_origin": "private_gateway",
                    "native_object_type": table_type,
                },
            },
        )

        table_asset, created = TableAsset.objects.update_or_create(
            data_source=data_source,
            schema_name=schema,
            table_name=name,
            defaults={
                "data_asset": asset,
                "object_type": (
                    TableAsset.ObjectType.VIEW
                    if table_type == "VIEW"
                    else TableAsset.ObjectType.TABLE
                ),
                "primary_key_columns": list(table.get("primary_key") or []),
            },
        )
        result["created_tables" if created else "updated_tables"] += 1
        lookup[(schema, name)] = table_asset

        seen = set()
        for column in table.get("columns") or []:
            seen.add(column["name"])
            _, field_created = FieldAsset.objects.update_or_create(
                table_asset=table_asset,
                name=column["name"],
                defaults={
                    "logical_type": column.get("data_type", "OTHER"),
                    "native_type": column.get("native_type", ""),
                    "ordinal_position": column.get("ordinal_position", 0),
                    "nullable": bool(column.get("nullable", True)),
                    "default_value": (
                        ""
                        if column.get("default") is None
                        else str(column.get("default"))
                    ),
                    "max_length": column.get("max_length"),
                    "numeric_precision": column.get("numeric_precision"),
                    "numeric_scale": column.get("numeric_scale"),
                    "is_primary_key": column["name"]
                    in (table.get("primary_key") or []),
                    "is_identity": bool(column.get("is_identity", False)),
                },
            )
            result["created_fields" if field_created else "updated_fields"] += 1

        stale = table_asset.fields.exclude(name__in=seen)
        result["deleted_fields"] += stale.count()
        stale.delete()

    for table in catalog:
        source = lookup.get((table["schema"], table["name"]))
        if source is None:
            continue
        for fk in table.get("foreign_keys") or []:
            target = lookup.get((fk["target_schema"], fk["target_table"]))
            if target is None:
                continue
            _, created = RelationAsset.objects.update_or_create(
                data_source=data_source,
                name=fk["name"],
                source_table=source,
                defaults={
                    "target_table": target,
                    "source_columns": list(fk.get("source_columns") or []),
                    "target_columns": list(fk.get("target_columns") or []),
                },
            )
            result["created_relations" if created else "updated_relations"] += 1

    return result
