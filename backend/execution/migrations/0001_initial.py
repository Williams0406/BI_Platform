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
            name="Execution",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("object_type", models.CharField(choices=[("SQL_TRANSFORMATION", "Transformación SQL"), ("DEPENDENCY_PROPAGATION", "Propagación de dependencias"), ("GENERIC", "Genérica")], max_length=50)),
                ("object_id", models.UUIDField(blank=True, null=True)),
                ("queue", models.CharField(default="fast", max_length=40)),
                ("status", models.CharField(choices=[("QUEUED", "En cola"), ("RUNNING", "Ejecutando"), ("SUCCESS", "Exitosa"), ("FAILED", "Fallida"), ("CANCELLED", "Cancelada"), ("BLOCKED", "Bloqueada")], default="QUEUED", max_length=20)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("celery_task_id", models.CharField(blank=True, max_length=255)),
                ("parameters", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("error_type", models.CharField(blank=True, max_length=255)),
                ("error_message", models.TextField(blank=True)),
                ("queued_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("duration_ms", models.PositiveBigIntegerField(blank=True, null=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="executions_requested", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="executions", to="workspaces.workspace")),
            ],
            options={"ordering": ["-queued_at"]},
        ),
        migrations.CreateModel(
            name="ExecutionLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("level", models.CharField(choices=[("INFO", "Info"), ("WARNING", "Warning"), ("ERROR", "Error")], default="INFO", max_length=10)),
                ("message", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("execution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="execution.execution")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddIndex(
            model_name="execution",
            index=models.Index(fields=["workspace", "status"], name="execution_e_workspa_f72dda_idx"),
        ),
        migrations.AddIndex(
            model_name="execution",
            index=models.Index(fields=["object_type", "object_id"], name="execution_e_object__3bd452_idx"),
        ),
    ]
