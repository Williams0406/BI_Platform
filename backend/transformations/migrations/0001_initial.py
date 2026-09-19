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
            name="SQLTransformation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("sql", models.TextField(help_text="Solo SELECT/WITH. Use {{asset:<uuid>}} para referenciar Data Assets.")),
                ("output_mode", models.CharField(choices=[("VIEW", "Vista"), ("TABLE", "Tabla materializada")], default="VIEW", max_length=20)),
                ("refresh_policy", models.CharField(choices=[("MANUAL", "Manual"), ("AUTO", "Automática"), ("SCHEDULED", "Programada")], default="MANUAL", max_length=20)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sql_transformations_created", to=settings.AUTH_USER_MODEL)),
                ("output_asset", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="producer_sql_transformation", to="datasources.dataasset")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sql_transformations", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="TransformationInput",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("alias", models.CharField(blank=True, max_length=120)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sql_transformation_inputs", to="datasources.dataasset")),
                ("transformation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inputs", to="transformations.sqltransformation")),
            ],
        ),
        migrations.AddConstraint(
            model_name="sqltransformation",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_sql_transformation_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="transformationinput",
            constraint=models.UniqueConstraint(fields=("transformation", "asset"), name="unique_transformation_input_asset"),
        ),
    ]
