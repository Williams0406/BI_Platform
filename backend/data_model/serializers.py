from rest_framework import serializers

from datasources.models import DataSource
from .models import FieldAsset, FieldContentRule, RelationAsset, TableAsset


class FieldContentRuleInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldContentRule
        fields = ["id", "mode", "expression", "dependencies", "enabled", "created_at", "updated_at"]


class FieldAssetSerializer(serializers.ModelSerializer):
    content_rule = FieldContentRuleInlineSerializer(read_only=True)
    editable_in_platform = serializers.SerializerMethodField()

    class Meta:
        model = FieldAsset
        fields = [
            "id", "name", "business_name", "description", "logical_type", "native_type",
            "ordinal_position", "nullable", "default_value", "max_length", "numeric_precision",
            "numeric_scale", "is_primary_key", "is_identity", "origin", "editable_in_platform",
            "content_rule",
        ]

    def get_editable_in_platform(self, obj):
        return obj.origin == FieldAsset.Origin.PLATFORM or obj.table_asset.data_source.mode == DataSource.Mode.MANAGED


class TableAssetSerializer(serializers.ModelSerializer):
    fields = FieldAssetSerializer(many=True, read_only=True)
    physical_identifier = serializers.SerializerMethodField()

    class Meta:
        model = TableAsset
        fields = [
            "id", "data_asset", "data_source", "schema_name", "table_name", "technical_name", "physical_identifier", "object_type",
            "primary_key_columns", "row_version_column", "discovered_at", "last_synced_at", "fields",
        ]

    def get_physical_identifier(self, obj):
        return f"{obj.schema_name}.{obj.table_name}"


class RelationAssetSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = RelationAsset
        fields = [
            "id", "name", "data_source", "source_table", "target_table", "source", "target",
            "source_columns", "target_columns", "cardinality", "cross_filter_direction", "is_active",
            "discovered_at", "last_synced_at",
        ]
        extra_kwargs = {
            "data_source": {"required": False},
            "name": {"required": False, "allow_blank": True},
            "source_columns": {"required": True},
            "target_columns": {"required": True},
        }

    def validate(self, attrs):
        source = attrs.get("source_table", getattr(self.instance, "source_table", None))
        target = attrs.get("target_table", getattr(self.instance, "target_table", None))
        source_columns = attrs.get("source_columns", getattr(self.instance, "source_columns", []))
        target_columns = attrs.get("target_columns", getattr(self.instance, "target_columns", []))
        if source and target and source.id == target.id:
            raise serializers.ValidationError("Una relación debe conectar dos tablas distintas.")
        if source and target and source.data_source.workspace_id != target.data_source.workspace_id:
            raise serializers.ValidationError("Las tablas deben pertenecer al mismo workspace.")
        if not source_columns or len(source_columns) != len(target_columns):
            raise serializers.ValidationError("Las columnas origen y destino deben tener la misma cardinalidad.")
        if source:
            valid = set(source.fields.values_list("name", flat=True))
            if any(column not in valid for column in source_columns):
                raise serializers.ValidationError("Una o más columnas origen no existen.")
        if target:
            valid = set(target.fields.values_list("name", flat=True))
            if any(column not in valid for column in target_columns):
                raise serializers.ValidationError("Una o más columnas destino no existen.")
        if source and target and not str(attrs.get("name", getattr(self.instance, "name", "")) or "").strip():
            source_name = source_columns[0] if source_columns else "field"
            target_name = target_columns[0] if target_columns else "field"
            attrs["name"] = f"{source.table_name}_{source_name}__{target.table_name}_{target_name}"[:240]
        attrs["data_source"] = source.data_source if source else attrs.get("data_source")
        return attrs

    def get_source(self, obj):
        return f"{obj.source_table.schema_name}.{obj.source_table.table_name}"

    def get_target(self, obj):
        return f"{obj.target_table.schema_name}.{obj.target_table.table_name}"


class FieldContentRuleSerializer(serializers.ModelSerializer):
    table_id = serializers.UUIDField(source="field.table_asset_id", read_only=True)
    field_name = serializers.CharField(source="field.name", read_only=True)

    class Meta:
        model = FieldContentRule
        fields = ["id", "field", "table_id", "field_name", "mode", "expression", "dependencies", "enabled", "created_at", "updated_at"]

    def validate(self, attrs):
        field = attrs.get("field", getattr(self.instance, "field", None))
        mode = attrs.get("mode", getattr(self.instance, "mode", FieldContentRule.Mode.MANUAL))
        expression = attrs.get("expression", getattr(self.instance, "expression", ""))
        if field and not (field.origin == FieldAsset.Origin.PLATFORM or field.table_asset.data_source.mode == DataSource.Mode.MANAGED):
            raise serializers.ValidationError("Los campos provenientes de una fuente External/Private Gateway son de solo lectura. Agregue un campo de plataforma para aplicar una regla.")
        if mode != FieldContentRule.Mode.MANUAL and not str(expression or "").strip():
            raise serializers.ValidationError({"expression": "La expresión es obligatoria para DAX, SQL o Python."})
        return attrs
