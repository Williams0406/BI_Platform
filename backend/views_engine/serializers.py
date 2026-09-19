from rest_framework import serializers

from data_model.models import FieldAsset
from workspaces.models import Membership

from .models import ViewActionRule, ViewDefinition, ViewFieldBinding


WRITE_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
]


REQUIRED_ROLES = {
    ViewDefinition.ViewType.KANBAN: {"TITLE", "STATUS"},
    ViewDefinition.ViewType.MATRIX: {"ROW", "COLUMN", "VALUE"},
    ViewDefinition.ViewType.CALENDAR: {"TITLE", "START_DATE"},
}


class ViewFieldBindingSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source="field.name", read_only=True)
    logical_type = serializers.CharField(source="field.logical_type", read_only=True)

    class Meta:
        model = ViewFieldBinding
        fields = [
            "id",
            "field",
            "field_name",
            "logical_type",
            "role",
            "alias",
            "editable",
            "required",
            "position",
            "options",
        ]
        read_only_fields = ["id"]


class ViewActionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewActionRule
        fields = [
            "id",
            "name",
            "action_type",
            "enabled",
            "config",
        ]
        read_only_fields = ["id"]


class ViewDefinitionSerializer(serializers.ModelSerializer):
    bindings = ViewFieldBindingSerializer(many=True, read_only=True)
    action_rules = ViewActionRuleSerializer(many=True, read_only=True)

    class Meta:
        model = ViewDefinition
        fields = [
            "id",
            "workspace",
            "source_table",
            "name",
            "view_type",
            "status",
            "config",
            "default_filters",
            "default_ordering",
            "bindings",
            "action_rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
        source_table = attrs.get(
            "source_table",
            getattr(self.instance, "source_table", None),
        )
        request = self.context["request"]

        if source_table and workspace:
            if source_table.data_source.workspace_id != workspace.id:
                raise serializers.ValidationError(
                    "La tabla fuente debe pertenecer al mismo workspace."
                )

            allowed = Membership.objects.filter(
                organization=workspace.organization,
                user=request.user,
                is_active=True,
                role__in=WRITE_ROLES,
            ).exists()
            if not allowed and self.instance is None:
                raise serializers.ValidationError(
                    "No tiene permisos para crear vistas en este workspace."
                )

        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class BindingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewFieldBinding
        fields = [
            "field",
            "role",
            "alias",
            "editable",
            "required",
            "position",
            "options",
        ]

    def validate_field(self, field):
        view = self.context["view"]
        if field.table_asset_id != view.source_table_id:
            raise serializers.ValidationError(
                "El campo debe pertenecer a la tabla fuente de la vista."
            )
        return field

    def validate(self, attrs):
        view = self.context["view"]
        role = attrs["role"]
        field = attrs["field"]

        if role in {"START_DATE", "END_DATE"} and field.logical_type not in {
            "DATE",
            "DATETIME",
            "DATETIME_TZ",
        }:
            raise serializers.ValidationError(
                f"{role} requiere un campo DATE/DATETIME/DATETIME_TZ."
            )

        if role == "VALUE" and view.view_type == ViewDefinition.ViewType.MATRIX:
            if field.logical_type not in {
                "INTEGER",
                "BIGINT",
                "DECIMAL",
                "FLOAT",
                "STRING",
                "TEXT",
            }:
                raise serializers.ValidationError(
                    "El VALUE de una matriz debe ser un campo escalar editable/visualizable."
                )

        return attrs


class ActionRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewActionRule
        fields = ["name", "action_type", "enabled", "config"]


class ViewInteractionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            "UPDATE_FIELD",
            "MOVE_KANBAN",
            "EDIT_CELL",
            "RESIZE_CALENDAR",
            "SUBMIT_FORM",
        ]
    )
    record_key = serializers.CharField()
    expected_version = serializers.IntegerField(min_value=1)
    values = serializers.DictField(child=serializers.JSONField(), allow_empty=False)


class ViewBuilderSerializer(serializers.Serializer):
    """Persist the declarative Operational View IR produced by the visual/code builder."""
    name = serializers.CharField(max_length=180, required=False)
    view_type = serializers.ChoiceField(choices=ViewDefinition.ViewType.choices, required=False)
    config = serializers.JSONField()
    bindings = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate_bindings(self, bindings):
        view = self.context["view"]
        field_ids = {
            str(field.id): field
            for field in FieldAsset.objects.filter(
                table_asset__data_source__workspace_id=view.workspace_id
            ).select_related("table_asset", "table_asset__data_source")
        }
        normalized = []
        for index, item in enumerate(bindings):
            field_id = str(item.get("field") or "")
            if field_id not in field_ids:
                raise serializers.ValidationError(f"Binding {index + 1}: el campo no pertenece a una tabla disponible en este workspace.")
            normalized.append({
                "field": field_ids[field_id],
                "role": item.get("role") or "DISPLAY",
                "alias": item.get("alias") or "",
                "editable": bool(item.get("editable", False)),
                "required": bool(item.get("required", False)),
                "position": int(item.get("position", index)),
                "options": item.get("options") or {},
            })
        return normalized
