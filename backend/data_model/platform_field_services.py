from django.db import connection, transaction

from datasources.models import DataSource
from .managed_services import build_sql_type, quote
from .models import FieldAsset


@transaction.atomic
def create_platform_field(*, table, definition):
    position = (table.fields.order_by("-ordinal_position").values_list("ordinal_position", flat=True).first() or 0) + 1
    native_type = f"platform_overlay:{definition['logical_type'].lower()}"

    if table.data_source.mode == DataSource.Mode.MANAGED:
        parts = [quote(definition["name"]), build_sql_type(definition)]
        if not definition.get("nullable", True):
            parts.append("NOT NULL")
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {quote(table.schema_name)}.{quote(table.table_name)} ADD COLUMN " + " ".join(parts)
            )
        native_type = build_sql_type(definition)

    field = FieldAsset.objects.create(
        table_asset=table,
        name=definition["name"],
        business_name=definition.get("business_name", ""),
        logical_type=definition["logical_type"],
        native_type=native_type,
        ordinal_position=position,
        nullable=definition.get("nullable", True),
        max_length=definition.get("max_length"),
        numeric_precision=definition.get("numeric_precision"),
        numeric_scale=definition.get("numeric_scale"),
        origin=FieldAsset.Origin.PLATFORM,
    )
    return field
