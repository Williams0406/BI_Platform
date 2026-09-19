from rest_framework import serializers

from datasources.models import DataAsset
from workspaces.models import Membership

from .models import MetricDefinition, SemanticDimension, SemanticModel


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


class SemanticDimensionSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source="field.name", read_only=True)
    logical_type = serializers.CharField(source="field.logical_type", read_only=True)

    class Meta:
        model = SemanticDimension
        fields = [
            "id",
            "semantic_model",
            "field",
            "field_name",
            "logical_type",
            "name",
            "dimension_type",
            "format",
            "hierarchy",
            "sort_order",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        semantic_model = attrs.get("semantic_model", getattr(self.instance, "semantic_model", None))
        field = attrs.get("field", getattr(self.instance, "field", None))
        if semantic_model and field and field.table_asset_id != semantic_model.base_table_id:
            raise serializers.ValidationError(
                "La dimensión debe usar un campo de la tabla base del SemanticModel."
            )
        return attrs


class MetricDefinitionSerializer(serializers.ModelSerializer):
    source_field_name = serializers.CharField(source="source_field.name", read_only=True)

    class Meta:
        model = MetricDefinition
        fields = [
            "id",
            "workspace",
            "semantic_model",
            "name",
            "description",
            "expression_type",
            "source_field",
            "source_field_name",
            "aggregation",
            "expression",
            "format_type",
            "unit",
            "decimal_places",
            "enabled",
            "cache_ttl_seconds",
            "data_asset",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "data_asset", "created_at", "updated_at"]

    def validate(self, attrs):
        workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
        semantic_model = attrs.get("semantic_model", getattr(self.instance, "semantic_model", None))
        source_field = attrs.get("source_field", getattr(self.instance, "source_field", None))
        expression_type = attrs.get(
            "expression_type",
            getattr(self.instance, "expression_type", MetricDefinition.ExpressionType.SIMPLE),
        )
        aggregation = attrs.get(
            "aggregation",
            getattr(self.instance, "aggregation", MetricDefinition.Aggregation.SUM),
        )

        if workspace and semantic_model and semantic_model.workspace_id != workspace.id:
            raise serializers.ValidationError(
                "SemanticModel y métrica deben pertenecer al mismo workspace."
            )

        if source_field and semantic_model and source_field.table_asset_id != semantic_model.base_table_id:
            raise serializers.ValidationError(
                "source_field debe pertenecer a la tabla base del SemanticModel."
            )

        if (
            expression_type == MetricDefinition.ExpressionType.SIMPLE
            and aggregation != MetricDefinition.Aggregation.COUNT
            and not source_field
        ):
            raise serializers.ValidationError(
                "Una métrica SIMPLE requiere source_field, excepto COUNT."
            )

        if expression_type in {MetricDefinition.ExpressionType.SQL, MetricDefinition.ExpressionType.DAX, MetricDefinition.ExpressionType.PYTHON} and not (attrs.get("expression", getattr(self.instance, "expression", "")) or "").strip():
            raise serializers.ValidationError(
                "La medida requiere una expresión o script."
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        workspace = validated_data["workspace"]
        allowed = Membership.objects.filter(
            organization=workspace.organization,
            user=request.user,
            is_active=True,
            role__in=WRITE_ROLES,
        ).exists()
        if not allowed:
            raise serializers.ValidationError(
                "No tiene permisos para crear métricas en este workspace."
            )

        metric = MetricDefinition.objects.create(
            created_by=request.user,
            **validated_data,
        )

        asset = DataAsset.objects.create(
            workspace=workspace,
            data_source=metric.semantic_model.base_table.data_source,
            name=metric.name,
            asset_type=DataAsset.AssetType.METRIC,
            status=DataAsset.Status.ACTIVE,
            metadata={
                "semantic_model_id": str(metric.semantic_model_id),
                "metric_id": str(metric.id),
            },
            created_by=request.user,
        )
        metric.data_asset = asset
        metric.save(update_fields=["data_asset", "updated_at"])
        return metric


class SemanticModelSerializer(serializers.ModelSerializer):
    dimensions = SemanticDimensionSerializer(many=True, read_only=True)
    metrics = MetricDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = SemanticModel
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "base_table",
            "enabled",
            "dimensions",
            "metrics",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
        base_table = attrs.get("base_table", getattr(self.instance, "base_table", None))
        if workspace and base_table and base_table.data_source.workspace_id != workspace.id:
            raise serializers.ValidationError(
                "La tabla base debe pertenecer al mismo workspace."
            )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        workspace = validated_data["workspace"]
        allowed = Membership.objects.filter(
            organization=workspace.organization,
            user=request.user,
            is_active=True,
            role__in=WRITE_ROLES,
        ).exists()
        if not allowed:
            raise serializers.ValidationError(
                "No tiene permisos para crear Semantic Models."
            )
        return SemanticModel.objects.create(
            created_by=request.user,
            **validated_data,
        )


class MetricQuerySerializer(serializers.Serializer):
    dimensions = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    filters = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )
    limit = serializers.IntegerField(default=1000, min_value=1, max_value=5000)
    use_cache = serializers.BooleanField(default=True)
