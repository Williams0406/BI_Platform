from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from metrics.query_engine import MetricQueryError

from .models import ChartDefinition, DashboardDefinition, DashboardItem, ReportDefinition
from .serializers import (
    AnalyticsQuerySerializer,
    ChartDefinitionSerializer,
    DashboardDefinitionSerializer,
    DashboardItemSerializer,
    ReportDefinitionSerializer,
)
from .services import chart_dataset, dashboard_dataset, drilldown


class ChartDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = ChartDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            ChartDefinition.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace", "metric")
            .prefetch_related("dimensions")
            .distinct()
        )
        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        return queryset

    @action(detail=True, methods=["post"], url_path="dataset")
    def dataset(self, request, pk=None):
        chart = self.get_object()
        serializer = AnalyticsQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(
                chart_dataset(
                    chart,
                    runtime_filters=serializer.validated_data.get("filters", []),
                    use_cache=serializer.validated_data["use_cache"],
                )
            )
        except MetricQueryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="drilldown")
    def drilldown_endpoint(self, request, pk=None):
        chart = self.get_object()
        serializer = AnalyticsQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(
                drilldown(
                    chart,
                    runtime_filters=serializer.validated_data.get("filters", []),
                    level=serializer.validated_data.get("drill_level"),
                    use_cache=serializer.validated_data["use_cache"],
                )
            )
        except MetricQueryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class DashboardDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            DashboardDefinition.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace")
            .prefetch_related("items__chart", "items__chart__dimensions")
            .distinct()
        )
        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        return queryset

    @action(detail=True, methods=["post"], url_path="dataset")
    def dataset(self, request, pk=None):
        dashboard = self.get_object()
        serializer = AnalyticsQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(
                dashboard_dataset(
                    dashboard,
                    runtime_filters=serializer.validated_data.get("filters", []),
                    use_cache=serializer.validated_data["use_cache"],
                )
            )
        except MetricQueryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class DashboardItemViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = DashboardItem.objects.filter(
            dashboard__workspace__organization__memberships__user=self.request.user,
            dashboard__workspace__organization__memberships__is_active=True,
        ).select_related("dashboard", "chart").distinct()

        dashboard = self.request.query_params.get("dashboard")
        if dashboard:
            queryset = queryset.filter(dashboard_id=dashboard)
        return queryset

    def perform_create(self, serializer):
        dashboard = serializer.validated_data["dashboard"]
        chart = serializer.validated_data["chart"]
        if chart.workspace_id != dashboard.workspace_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Chart y dashboard deben pertenecer al mismo workspace.")
        serializer.save()


class ReportDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = ReportDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ReportDefinition.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related("workspace", "dashboard").distinct()

        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        return queryset
