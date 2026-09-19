import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("data_model", "0002_tableasset_row_version_column"),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ViewDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("view_type", models.CharField(choices=[("TABLE", "Tabla"), ("SPREADSHEET", "Hoja de cálculo"), ("KANBAN", "Kanban"), ("MATRIX", "Matriz"), ("FORM", "Formulario"), ("CALENDAR", "Calendario")], max_length=30)),
                ("status", models.CharField(choices=[("ACTIVE", "Activa"), ("ARCHIVED", "Archivada")], default="ACTIVE", max_length=20)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("default_filters", models.JSONField(blank=True, default=list)),
                ("default_ordering", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="views_created", to=settings.AUTH_USER_MODEL)),
                ("source_table", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="views", to="data_model.tableasset")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="view_definitions", to="workspaces.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ViewFieldBinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("DISPLAY", "Display"), ("TITLE", "Title"), ("SUBTITLE", "Subtitle"), ("STATUS", "Status"), ("GROUP", "Group"), ("ROW", "Row"), ("COLUMN", "Column"), ("VALUE", "Value"), ("START_DATE", "Start date"), ("END_DATE", "End date"), ("LABEL", "Label"), ("COLOR", "Color"), ("SORT", "Sort"), ("HIDDEN", "Hidden")], max_length=30)),
                ("alias", models.CharField(blank=True, max_length=180)),
                ("editable", models.BooleanField(default=False)),
                ("required", models.BooleanField(default=False)),
                ("position", models.PositiveIntegerField(default=0)),
                ("options", models.JSONField(blank=True, default=dict)),
                ("field", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="view_bindings", to="data_model.fieldasset")),
                ("view", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bindings", to="views_engine.viewdefinition")),
            ],
            options={"ordering": ["position", "role", "field__ordinal_position"]},
        ),
        migrations.CreateModel(
            name="ViewActionRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("action_type", models.CharField(choices=[("UPDATE_FIELD", "Actualizar campo"), ("MOVE_KANBAN", "Mover tarjeta Kanban"), ("EDIT_CELL", "Editar celda"), ("RESIZE_CALENDAR", "Cambiar fecha/rango"), ("SUBMIT_FORM", "Enviar formulario")], max_length=40)),
                ("enabled", models.BooleanField(default=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("view", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="action_rules", to="views_engine.viewdefinition")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="viewdefinition",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_view_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="viewfieldbinding",
            constraint=models.UniqueConstraint(fields=("view", "field", "role"), name="unique_view_field_role_binding"),
        ),
    ]
