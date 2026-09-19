from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from datasources.models import DataAsset

from .models import MetricDefinition, SemanticDimension, SemanticModel
from .query_engine import MetricQueryError, execute_metric
from .serializers import (
    MetricDefinitionSerializer,
    MetricQuerySerializer,
    SemanticDimensionSerializer,
    SemanticModelSerializer,
)


class WorkspaceScopedQuerysetMixin:
    def scope_queryset(self, queryset):
        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        return queryset


class SemanticModelViewSet(WorkspaceScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = SemanticModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SemanticModel.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related("workspace", "base_table").prefetch_related(
            "dimensions__field",
            "metrics__source_field",
        ).distinct()
        return self.scope_queryset(queryset)

    def perform_destroy(self, instance):
        metric_asset_ids = list(instance.metrics.exclude(data_asset_id=None).values_list("data_asset_id", flat=True))
        instance.delete()
        if metric_asset_ids:
            DataAsset.objects.filter(id__in=metric_asset_ids).delete()


class SemanticDimensionViewSet(viewsets.ModelViewSet):
    serializer_class = SemanticDimensionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SemanticDimension.objects.filter(
            semantic_model__workspace__organization__memberships__user=self.request.user,
            semantic_model__workspace__organization__memberships__is_active=True,
        ).select_related(
            "semantic_model",
            "field",
        ).distinct()

        semantic_model = self.request.query_params.get("semantic_model")
        if semantic_model:
            queryset = queryset.filter(semantic_model_id=semantic_model)
        return queryset


class MetricDefinitionViewSet(WorkspaceScopedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = MetricDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = MetricDefinition.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related(
            "workspace",
            "semantic_model",
            "semantic_model__base_table",
            "source_field",
            "data_asset",
        ).distinct()
        return self.scope_queryset(queryset)

    @action(detail=True, methods=["post"], url_path="query")
    def query_metric(self, request, pk=None):
        metric = self.get_object()
        serializer = MetricQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = execute_metric(
                metric,
                dimension_ids=serializer.validated_data.get("dimensions", []),
                filters=serializer.validated_data.get("filters", []),
                limit=serializer.validated_data["limit"],
                use_cache=serializer.validated_data["use_cache"],
            )
            return Response(result)
        except MetricQueryError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
