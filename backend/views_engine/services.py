from collections import defaultdict

from data_records.services import list_records, update_record

from .models import ViewDefinition


def _binding_map(view):
    role_map = defaultdict(list)
    for binding in view.bindings.select_related("field").all():
        role_map[binding.role].append(binding)
    return role_map


def validate_view_contract(view):
    role_map = _binding_map(view)

    required = {
        ViewDefinition.ViewType.KANBAN: {"TITLE", "STATUS"},
        ViewDefinition.ViewType.MATRIX: {"ROW", "COLUMN", "VALUE"},
        ViewDefinition.ViewType.CALENDAR: {"TITLE", "START_DATE"},
    }.get(view.view_type, set())

    missing = [role for role in required if not role_map.get(role)]
    if missing:
        return {
            "valid": False,
            "missing_roles": sorted(missing),
        }

    if view.view_type == ViewDefinition.ViewType.FORM:
        editable = [b for items in role_map.values() for b in items if b.editable]
        if not editable:
            return {
                "valid": False,
                "missing_roles": [],
                "detail": "FORM requiere al menos un binding editable.",
            }

    return {"valid": True, "missing_roles": []}


def view_schema(view):
    role_map = _binding_map(view)

    return {
        "id": str(view.id),
        "name": view.name,
        "view_type": view.view_type,
        "status": view.status,
        "source_table": {
            "id": str(view.source_table_id),
            "schema": view.source_table.schema_name,
            "table": view.source_table.table_name,
            "primary_key": list(view.source_table.primary_key_columns or []),
            "row_version_column": view.source_table.row_version_column,
        },
        "config": view.config,
        "default_filters": view.default_filters,
        "default_ordering": view.default_ordering,
        "bindings": [
            {
                "id": str(binding.id),
                "field_id": str(binding.field_id),
                "field": binding.field.name,
                "logical_type": binding.field.logical_type,
                "role": binding.role,
                "alias": binding.alias or binding.field.business_name or binding.field.name,
                "editable": binding.editable,
                "required": binding.required,
                "position": binding.position,
                "options": binding.options,
            }
            for binding in view.bindings.select_related("field").all()
        ],
        "contract": validate_view_contract(view),
    }


def view_data(view, query_params):
    # Reuse the Phase 4 record engine. This keeps one source of truth for
    # pagination/filtering/order and later lets us swap providers by datasource.
    return list_records(view.source_table, query_params)


def _editable_field_names(view):
    return {
        binding.field.name
        for binding in view.bindings.select_related("field").all()
        if binding.editable
    }


def _fields_for_role(view, role):
    return [
        binding.field.name
        for binding in view.bindings.select_related("field").filter(role=role)
    ]


def translate_interaction(view, action, values):
    editable = _editable_field_names(view)

    if action == "MOVE_KANBAN":
        allowed = set(_fields_for_role(view, "STATUS"))
    elif action == "EDIT_CELL":
        allowed = set(_fields_for_role(view, "VALUE")) | editable
    elif action == "RESIZE_CALENDAR":
        allowed = (
            set(_fields_for_role(view, "START_DATE"))
            | set(_fields_for_role(view, "END_DATE"))
        )
    elif action in {"UPDATE_FIELD", "SUBMIT_FORM"}:
        allowed = editable
    else:
        allowed = set()

    unknown = set(values) - allowed
    if unknown:
        raise ValueError(
            "La interacción intentó modificar campos no autorizados por el binding: "
            + ", ".join(sorted(unknown))
        )

    if not values:
        raise ValueError("La interacción no contiene valores.")

    return values


def execute_interaction(view, record_key, expected_version, action, values):
    payload = translate_interaction(view, action, values)
    return update_record(
        view.source_table,
        record_key,
        payload,
        expected_version=expected_version,
    )
