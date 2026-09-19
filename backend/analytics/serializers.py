from rest_framework import serializers

from metrics.models import SemanticDimension
from workspaces.models import Membership

from .models import ChartDefinition, DashboardDefinition, DashboardItem, ReportDefinition


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


class ChartDefinitionSerializer(serializers.ModelSerializer):
    dimensions = serializers.PrimaryKeyRelatedField(
        queryset=SemanticDimension.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = ChartDefinition
        fields = [
            "id",
            "workspace",
            "name",
            "chart_type",
            "metric",
            "dimensions",
            "config",
            "default_filters",
            "sort_order",
            "limit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
        metric = attrs.get("metric", getattr(self.instance, "metric", None))
        dimensions = attrs.get("dimensions", None)

        if workspace and metric and metric.workspace_id != workspace.id:
            raise serializers.ValidationError(
                "La métrica debe pertenecer al mismo workspace."
            )

        if dimensions is not None and metric:
            bad = [
                dimension
                for dimension in dimensions
                if dimension.semantic_model_id != metric.semantic_model_id
            ]
            if bad:
                raise serializers.ValidationError(
                    "Todas las dimensiones deben pertenecer al SemanticModel de la métrica."
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        dimensions = validated_data.pop("dimensions", [])
        workspace = validated_data["workspace"]

        allowed = Membership.objects.filter(
            organization=workspace.organization,
            user=request.user,
            is_active=True,
            role__in=WRITE_ROLES,
        ).exists()
        if not allowed:
            raise serializers.ValidationError(
                "No tiene permisos para crear gráficos."
            )

        chart = ChartDefinition.objects.create(
            created_by=request.user,
            **validated_data,
        )
        chart.dimensions.set(dimensions)
        return chart


class DashboardItemSerializer(serializers.ModelSerializer):
    chart_name = serializers.CharField(source="chart.name", read_only=True)

    class Meta:
        model = DashboardItem
        fields = [
            "id",
            "dashboard",
            "chart",
            "chart_name",
            "position",
            "title_override",
            "config_override",
        ]
        read_only_fields = ["id"]


class DashboardDefinitionSerializer(serializers.ModelSerializer):
    items = DashboardItemSerializer(many=True, read_only=True)

    class Meta:
        model = DashboardDefinition
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "layout",
            "global_filters",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

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
                "No tiene permisos para crear dashboards."
            )
        return DashboardDefinition.objects.create(
            created_by=request.user,
            **validated_data,
        )


class ReportDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportDefinition
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "dashboard",
            "config",
            "default_export_format",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
        dashboard = attrs.get("dashboard", getattr(self.instance, "dashboard", None))
        if workspace and dashboard and dashboard.workspace_id != workspace.id:
            raise serializers.ValidationError(
                "El dashboard debe pertenecer al mismo workspace."
            )
        return attrs

    def create(self, validated_data):
        return ReportDefinition.objects.create(
            created_by=self.context["request"].user,
            **validated_data,
        )


class AnalyticsQuerySerializer(serializers.Serializer):
    filters = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )
    use_cache = serializers.BooleanField(default=True)
    drill_level = serializers.IntegerField(required=False, min_value=1)
