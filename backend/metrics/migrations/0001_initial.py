import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("data_model", "0002_tableasset_row_version_column"),
        ("datasources", "0001_initial"),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SemanticModel",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("base_table", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="semantic_models", to="data_model.tableasset")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="semantic_models_created", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="semantic_models", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SemanticDimension",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("dimension_type", models.CharField(choices=[("CATEGORY", "Categoría"), ("DATE", "Fecha"), ("DATETIME", "Fecha y hora"), ("NUMBER", "Número"), ("TEXT", "Texto")], default="CATEGORY", max_length=20)),
                ("format", models.CharField(blank=True, max_length=120)),
                ("hierarchy", models.JSONField(blank=True, default=list)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("field", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="semantic_dimensions", to="data_model.fieldasset")),
                ("semantic_model", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dimensions", to="metrics.semanticmodel")),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="MetricDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("expression_type", models.CharField(choices=[("SIMPLE", "Simple"), ("SQL", "SQL")], default="SIMPLE", max_length=20)),
                ("aggregation", models.CharField(choices=[("SUM", "Suma"), ("AVG", "Promedio"), ("MIN", "Mínimo"), ("MAX", "Máximo"), ("COUNT", "Conteo"), ("COUNT_DISTINCT", "Conteo distinto"), ("NONE", "Sin agregación")], default="SUM", max_length=30)),
                ("expression", models.TextField(blank=True)),
                ("format_type", models.CharField(choices=[("NUMBER", "Número"), ("INTEGER", "Entero"), ("PERCENT", "Porcentaje"), ("CURRENCY", "Moneda"), ("DURATION", "Duración"), ("CUSTOM", "Personalizado")], default="NUMBER", max_length=20)),
                ("unit", models.CharField(blank=True, max_length=40)),
                ("decimal_places", models.PositiveSmallIntegerField(default=2)),
                ("enabled", models.BooleanField(default=True)),
                ("cache_ttl_seconds", models.PositiveIntegerField(default=60)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="metrics_created", to=settings.AUTH_USER_MODEL)),
                ("data_asset", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="metric_definition", to="datasources.dataasset")),
                ("semantic_model", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="metrics.semanticmodel")),
                ("source_field", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="metrics", to="data_model.fieldasset")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metric_definitions", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="semanticmodel",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_semantic_model_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="semanticdimension",
            constraint=models.UniqueConstraint(fields=("semantic_model", "name"), name="unique_dimension_name_per_semantic_model"),
        ),
        migrations.AddConstraint(
            model_name="metricdefinition",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_metric_name_per_workspace"),
        ),
    ]
