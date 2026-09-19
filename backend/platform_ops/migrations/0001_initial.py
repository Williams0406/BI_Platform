import uuid
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [("workspaces", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="OperationalMetricSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("captured_at", models.DateTimeField(auto_now_add=True)),
                ("api", models.JSONField(blank=True, default=dict)),
                ("database", models.JSONField(blank=True, default=dict)),
                ("executions", models.JSONField(blank=True, default=dict)),
                ("gateways", models.JSONField(blank=True, default=dict)),
                ("storage", models.JSONField(blank=True, default=dict)),
            ],
            options={"ordering": ["-captured_at"]},
        ),
        migrations.CreateModel(
            name="WorkspacePlacement",
            fields=[
                ("workspace", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="placement", serialize=False, to="workspaces.workspace")),
                ("database_cluster", models.CharField(default="primary", max_length=120)),
                ("compute_pool", models.CharField(default="default", max_length=120)),
                ("storage_prefix", models.CharField(blank=True, max_length=255)),
                ("region", models.CharField(blank=True, max_length=80)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
