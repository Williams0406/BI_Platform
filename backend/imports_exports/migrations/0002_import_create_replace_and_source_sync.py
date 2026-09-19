from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("imports_exports", "0001_initial"),
        ("data_model", "0002_tableasset_row_version_column"),
        ("datasources", "0001_initial"),
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importjob",
            name="target_table",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="import_jobs", to="data_model.tableasset"),
        ),
        migrations.AlterField(
            model_name="importjob",
            name="mode",
            field=models.CharField(choices=[("CREATE", "Create new table"), ("APPEND", "Append"), ("REPLACE", "Replace"), ("UPSERT", "Upsert")], default="CREATE", max_length=10),
        ),
        migrations.AddField(model_name="importjob", name="target_table_name", field=models.CharField(blank=True, max_length=63)),
        migrations.AddField(model_name="importjob", name="target_display_name", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="importjob", name="inferred_schema", field=models.JSONField(blank=True, default=list)),
        migrations.CreateModel(
            name="SourceSyncPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("target_table_name", models.CharField(max_length=63)),
                ("target_display_name", models.CharField(blank=True, max_length=180)),
                ("strategy", models.CharField(choices=[("FULL", "Full refresh"), ("INCREMENTAL", "Incremental refresh")], default="FULL", max_length=20)),
                ("schedule", models.CharField(choices=[("MANUAL", "Manual"), ("HOURLY", "Hourly"), ("DAILY", "Daily"), ("WEEKLY", "Weekly"), ("CUSTOM", "Custom")], default="MANUAL", max_length=20)),
                ("custom_interval_minutes", models.PositiveIntegerField(default=60)),
                ("incremental_field", models.CharField(blank=True, max_length=180)),
                ("last_cursor_value", models.JSONField(blank=True, null=True)),
                ("enabled", models.BooleanField(default=True)),
                ("status", models.CharField(choices=[("IDLE", "Idle"), ("QUEUED", "Queued"), ("RUNNING", "Running"), ("SUCCESS", "Success"), ("FAILED", "Failed")], default="IDLE", max_length=20)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("next_run_at", models.DateTimeField(blank=True, null=True)),
                ("last_rows", models.PositiveBigIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("execution_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="source_sync_policies_created", to="identity.user")),
                ("source_data_source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sync_policies", to="datasources.datasource")),
                ("source_table", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_sync_policies", to="data_model.tableasset")),
                ("target_table", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="target_sync_policies", to="data_model.tableasset")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_sync_policies", to="workspaces.workspace")),
            ],
            options={"ordering": ["source_data_source__name", "source_table__schema_name", "source_table__table_name"]},
        ),
        migrations.AddConstraint(
            model_name="sourcesyncpolicy",
            constraint=models.UniqueConstraint(fields=("source_table", "target_table_name"), name="unique_source_table_sync_target_name"),
        ),
    ]
