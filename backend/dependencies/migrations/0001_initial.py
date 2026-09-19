import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("datasources", "0001_initial"),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetState",
            fields=[
                ("status", models.CharField(choices=[("FRESH", "Actualizado"), ("STALE", "Desactualizado"), ("RUNNING", "Ejecutando"), ("FAILED", "Fallido"), ("BLOCKED", "Bloqueado"), ("ARCHIVED", "Archivado")], default="FRESH", max_length=20)),
                ("version", models.PositiveBigIntegerField(default=1)),
                ("last_changed_at", models.DateTimeField(auto_now=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("asset", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="dependency_state", serialize=False, to="datasources.dataasset")),
            ],
        ),
        migrations.CreateModel(
            name="ChangeEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("change_type", models.CharField(choices=[("INSERT", "Insert"), ("UPDATE", "Update"), ("DELETE", "Delete"), ("REFRESH", "Refresh"), ("STRUCTURE", "Structure")], max_length=20)),
                ("record_key", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("propagated_at", models.DateTimeField(blank=True, null=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="change_events", to="datasources.dataasset")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="change_events_created", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="change_events", to="workspaces.workspace")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AssetDependency",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("dependency_type", models.CharField(choices=[("DATA", "Datos"), ("CALCULATION", "Cálculo"), ("MODEL_INPUT", "Input de modelo"), ("VISUALIZATION", "Visualización")], default="DATA", max_length=30)),
                ("refresh_policy", models.CharField(choices=[("AUTO", "Automática"), ("MARK_STALE", "Marcar desactualizado"), ("MANUAL", "Manual")], default="MARK_STALE", max_length=20)),
                ("active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("downstream", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="upstream_dependencies", to="datasources.dataasset")),
                ("upstream", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="downstream_dependencies", to="datasources.dataasset")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_dependencies", to="workspaces.workspace")),
            ],
        ),
        migrations.AddConstraint(
            model_name="assetdependency",
            constraint=models.UniqueConstraint(fields=("upstream", "downstream"), name="unique_asset_dependency_edge"),
        ),
        migrations.AddConstraint(
            model_name="assetdependency",
            constraint=models.CheckConstraint(condition=~models.Q(upstream=models.F("downstream")), name="dependency_no_self_loop"),
        ),
    ]
