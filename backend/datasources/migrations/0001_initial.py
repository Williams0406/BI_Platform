import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataSource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("mode", models.CharField(choices=[("MANAGED", "Administrada por la plataforma"), ("EXTERNAL", "Base externa"), ("PRIVATE_GATEWAY", "Gateway privado")], max_length=30)),
                ("engine", models.CharField(choices=[("PLATFORM_POSTGRES", "PostgreSQL administrado"), ("POSTGRESQL", "PostgreSQL"), ("SQLSERVER", "Microsoft SQL Server"), ("OTHER", "Otro")], max_length=40)),
                ("status", models.CharField(choices=[("DRAFT", "Borrador"), ("ACTIVE", "Activa"), ("UNAVAILABLE", "No disponible"), ("ARCHIVED", "Archivada")], default="DRAFT", max_length=20)),
                ("can_read", models.BooleanField(default=True)),
                ("can_write", models.BooleanField(default=False)),
                ("can_ddl", models.BooleanField(default=False)),
                ("connection_metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="data_sources_created", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="data_sources", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="DataAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("asset_type", models.CharField(choices=[("TABLE", "Tabla"), ("VIEW", "Vista"), ("DERIVED_TABLE", "Tabla derivada"), ("DATASET", "Dataset"), ("METRIC", "Métrica"), ("CHART", "Gráfico"), ("DASHBOARD", "Dashboard"), ("REPORT", "Reporte"), ("ML_MODEL", "Modelo ML"), ("OPTIMIZATION_MODEL", "Modelo de optimización"), ("OTHER", "Otro")], max_length=40)),
                ("status", models.CharField(choices=[("ACTIVE", "Activo"), ("STALE", "Desactualizado"), ("ARCHIVED", "Archivado")], default="ACTIVE", max_length=20)),
                ("physical_schema", models.CharField(blank=True, max_length=180)),
                ("physical_name", models.CharField(blank=True, max_length=180)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveBigIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="data_assets_created", to=settings.AUTH_USER_MODEL)),
                ("data_source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assets", to="datasources.datasource")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="data_assets", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="datasource",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_datasource_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="dataasset",
            constraint=models.UniqueConstraint(fields=("workspace", "name", "asset_type"), name="unique_asset_name_type_per_workspace"),
        ),
    ]
