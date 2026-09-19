import uuid

from django.conf import settings
from django.db import models

from metrics.models import MetricDefinition, SemanticDimension
from workspaces.models import Workspace


class ChartDefinition(models.Model):
    class ChartType(models.TextChoices):
        KPI = "KPI", "KPI"
        TABLE = "TABLE", "Tabla"
        BAR = "BAR", "Barras"
        LINE = "LINE", "Línea"
        AREA = "AREA", "Área"
        PIE = "PIE", "Pie"
        DONUT = "DONUT", "Donut"
        SCATTER = "SCATTER", "Dispersión"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="chart_definitions",
    )
    name = models.CharField(max_length=180)
    chart_type = models.CharField(max_length=20, choices=ChartType.choices)

    metric = models.ForeignKey(
        MetricDefinition,
        on_delete=models.CASCADE,
        related_name="charts",
    )
    dimensions = models.ManyToManyField(
        SemanticDimension,
        blank=True,
        related_name="charts",
    )

    config = models.JSONField(default=dict, blank=True)
    default_filters = models.JSONField(default=list, blank=True)
    sort_order = models.JSONField(default=list, blank=True)
    limit = models.PositiveIntegerField(default=1000)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="charts_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_chart_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name


class DashboardDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="dashboards",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    layout = models.JSONField(default=dict, blank=True)
    global_filters = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dashboards_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_dashboard_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name


class DashboardItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(
        DashboardDefinition,
        on_delete=models.CASCADE,
        related_name="items",
    )
    chart = models.ForeignKey(
        ChartDefinition,
        on_delete=models.CASCADE,
        related_name="dashboard_items",
    )
    position = models.JSONField(default=dict)
    title_override = models.CharField(max_length=180, blank=True)
    config_override = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dashboard", "chart"],
                name="unique_chart_per_dashboard",
            )
        ]


class ReportDefinition(models.Model):
    class ExportFormat(models.TextChoices):
        PDF = "PDF", "PDF"
        XLSX = "XLSX", "Excel"
        CSV = "CSV", "CSV"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    dashboard = models.ForeignKey(
        DashboardDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    config = models.JSONField(default=dict, blank=True)
    default_export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.PDF,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_report_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name
