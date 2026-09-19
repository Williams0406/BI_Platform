# Generated for Focused UX v12
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def mark_existing_managed_fields(apps, schema_editor):
    FieldAsset = apps.get_model("data_model", "FieldAsset")
    FieldAsset.objects.filter(table_asset__data_source__mode="MANAGED").update(origin="PLATFORM")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("data_model", "0002_tableasset_row_version_column"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="fieldasset",
            name="origin",
            field=models.CharField(choices=[("SOURCE", "Source"), ("PLATFORM", "Platform")], default="SOURCE", max_length=20),
        ),
        migrations.RunPython(mark_existing_managed_fields, noop),
        migrations.CreateModel(
            name="FieldContentRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("mode", models.CharField(choices=[("MANUAL", "Manual"), ("DAX", "DAX"), ("SQL", "SQL"), ("PYTHON", "Python")], default="MANUAL", max_length=20)),
                ("expression", models.TextField(blank=True)),
                ("dependencies", models.JSONField(blank=True, default=list)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="field_content_rules_created", to=settings.AUTH_USER_MODEL)),
                ("field", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="content_rule", to="data_model.fieldasset")),
            ],
            options={"ordering": ["field__table_asset__table_name", "field__ordinal_position"]},
        ),
    ]
