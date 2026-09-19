import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("metrics", "0001_initial"),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChartDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("chart_type", models.CharField(choices=[("KPI", "KPI"), ("TABLE", "Tabla"), ("BAR", "Barras"), ("LINE", "Línea"), ("AREA", "Área"), ("PIE", "Pie"), ("DONUT", "Donut"), ("SCATTER", "Dispersión")], max_length=20)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("default_filters", models.JSONField(blank=True, default=list)),
                ("sort_order", models.JSONField(blank=True, default=list)),
                ("limit", models.PositiveIntegerField(default=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="charts_created", to=settings.AUTH_USER_MODEL)),
                ("metric", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="charts", to="metrics.metricdefinition")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chart_definitions", to="workspaces.workspace")),
                ("dimensions", models.ManyToManyField(blank=True, related_name="charts", to="metrics.semanticdimension")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DashboardDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("layout", models.JSONField(blank=True, default=dict)),
                ("global_filters", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dashboards_created", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dashboards", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DashboardItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("position", models.JSONField(default=dict)),
                ("title_override", models.CharField(blank=True, max_length=180)),
                ("config_override", models.JSONField(blank=True, default=dict)),
                ("chart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dashboard_items", to="analytics.chartdefinition")),
                ("dashboard", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="analytics.dashboarddefinition")),
            ],
        ),
        migrations.CreateModel(
            name="ReportDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("default_export_format", models.CharField(choices=[("PDF", "PDF"), ("XLSX", "Excel"), ("CSV", "CSV")], default="PDF", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reports_created", to=settings.AUTH_USER_MODEL)),
                ("dashboard", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reports", to="analytics.dashboarddefinition")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="chartdefinition",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_chart_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="dashboarddefinition",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_dashboard_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="dashboarditem",
            constraint=models.UniqueConstraint(fields=("dashboard", "chart"), name="unique_chart_per_dashboard"),
        ),
        migrations.AddConstraint(
            model_name="reportdefinition",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_report_name_per_workspace"),
        ),
    ]
