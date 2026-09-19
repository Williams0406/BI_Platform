"""Central table identity helpers.

User-authored SQL/Python/DAX and normal UI should use ``technical_name``.
``schema_name`` is infrastructure metadata and must not be required from users.
"""
from .models import TableAsset


def technical_name(table: TableAsset) -> str:
    return table.technical_name or table.table_name


def physical_identifier(table: TableAsset) -> str:
    return f"{table.schema_name}.{table.table_name}"


def resolve_table(workspace, name: str) -> TableAsset:
    """Resolve a user-facing technical table name inside one workspace.

    Keeping the lookup workspace-scoped lets two workspaces safely expose the
    same technical name while their physical schemas remain isolated.
    """
    value = str(name or "").strip()
    if not value:
        raise TableAsset.DoesNotExist("Technical table name is required.")
    return TableAsset.objects.select_related("data_source").get(
        data_source__workspace=workspace,
        technical_name=value,
    )
