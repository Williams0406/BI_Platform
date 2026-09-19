import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("datasources", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TableAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("schema_name", models.CharField(max_length=180)),
                ("table_name", models.CharField(max_length=180)),
                ("object_type", models.CharField(choices=[("TABLE", "Tabla"), ("VIEW", "Vista")], default="TABLE", max_length=10)),
                ("primary_key_columns", models.JSONField(blank=True, default=list)),
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                ("last_synced_at", models.DateTimeField(auto_now=True)),
                ("data_asset", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="table_definition", to="datasources.dataasset")),
                ("data_source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="table_assets", to="datasources.datasource")),
            ],
            options={"ordering": ["schema_name", "table_name"]},
        ),
        migrations.CreateModel(
            name="FieldAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("logical_type", models.CharField(max_length=40)),
                ("native_type", models.CharField(max_length=120)),
                ("ordinal_position", models.PositiveIntegerField()),
                ("nullable", models.BooleanField(default=True)),
                ("default_value", models.TextField(blank=True)),
                ("max_length", models.IntegerField(blank=True, null=True)),
                ("numeric_precision", models.IntegerField(blank=True, null=True)),
                ("numeric_scale", models.IntegerField(blank=True, null=True)),
                ("is_primary_key", models.BooleanField(default=False)),
                ("is_identity", models.BooleanField(default=False)),
                ("business_name", models.CharField(blank=True, max_length=180)),
                ("description", models.TextField(blank=True)),
                ("table_asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fields", to="data_model.tableasset")),
            ],
            options={"ordering": ["ordinal_position"]},
        ),
        migrations.CreateModel(
            name="RelationAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=240)),
                ("source_columns", models.JSONField(default=list)),
                ("target_columns", models.JSONField(default=list)),
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                ("last_synced_at", models.DateTimeField(auto_now=True)),
                ("data_source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="relation_assets", to="datasources.datasource")),
                ("source_table", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_relations", to="data_model.tableasset")),
                ("target_table", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_relations", to="data_model.tableasset")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="tableasset",
            constraint=models.UniqueConstraint(fields=("data_source", "schema_name", "table_name"), name="unique_catalog_table_per_source"),
        ),
        migrations.AddConstraint(
            model_name="fieldasset",
            constraint=models.UniqueConstraint(fields=("table_asset", "name"), name="unique_field_per_catalog_table"),
        ),
        migrations.AddConstraint(
            model_name="relationasset",
            constraint=models.UniqueConstraint(fields=("data_source", "name", "source_table"), name="unique_relation_per_source_name_table"),
        ),
    ]
