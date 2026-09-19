import re

from django.db import connection

from datasources.models import DataAsset
from data_model.models import TableAsset


ASSET_TOKEN = re.compile(
    r"\{\{asset:([0-9a-fA-F-]{36})\}\}"
)

FORBIDDEN_KEYWORDS = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
    r"COPY|CALL|DO|VACUUM|ANALYZE|COMMENT|SET|RESET"
    r")\b",
    re.IGNORECASE,
)


class SQLValidationError(ValueError):
    pass


def validate_select_sql(sql_text):
    normalized = sql_text.strip()

    if not normalized:
        raise SQLValidationError("La transformación SQL está vacía.")

    if ";" in normalized:
        raise SQLValidationError(
            "No se permiten múltiples sentencias ni punto y coma."
        )

    if not re.match(r"^(SELECT|WITH)\b", normalized, re.IGNORECASE):
        raise SQLValidationError(
            "La transformación debe comenzar con SELECT o WITH."
        )

    if FORBIDDEN_KEYWORDS.search(normalized):
        raise SQLValidationError(
            "La transformación contiene una operación no permitida."
        )

    return normalized


def quote(identifier):
    return connection.ops.quote_name(identifier)


def resolve_asset_tokens(sql_text, workspace):
    used_assets = []

    def replace(match):
        asset_id = match.group(1)
        try:
            asset = DataAsset.objects.get(id=asset_id, workspace=workspace)
        except DataAsset.DoesNotExist as exc:
            raise SQLValidationError(
                f"DataAsset no encontrado en el workspace: {asset_id}"
            ) from exc

        try:
            table = asset.table_definition
        except TableAsset.DoesNotExist as exc:
            raise SQLValidationError(
                f"El asset {asset.name} no es tabular."
            ) from exc

        # Phase 6 SQL execution currently targets the Control Plane PostgreSQL
        # connection, so only MANAGED tables are executable directly.
        if asset.data_source.mode != "MANAGED":
            raise SQLValidationError(
                f"El asset {asset.name} es EXTERNAL. "
                "Para SQL cross-source será necesario el execution adapter posterior."
            )

        used_assets.append(asset)
        return f"{quote(table.schema_name)}.{quote(table.table_name)}"

    rendered = ASSET_TOKEN.sub(replace, sql_text)
    return rendered, used_assets
