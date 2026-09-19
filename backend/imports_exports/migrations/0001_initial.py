import uuid
from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("data_model","0002_tableasset_row_version_column"),
        ("workspaces","0001_initial"),
        ("execution","0004_execution_object_types_phase10"),
    ]
    operations=[
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("file",models.FileField(upload_to="imports/%Y/%m/%d/")),
                ("file_type",models.CharField(choices=[("CSV","CSV"),("XLSX","Excel")],max_length=10)),
                ("sheet_name",models.CharField(blank=True,max_length=180)),
                ("mode",models.CharField(choices=[("APPEND","Append"),("UPSERT","Upsert")],default="APPEND",max_length=10)),
                ("column_mapping",models.JSONField(blank=True,default=dict)),
                ("status",models.CharField(choices=[("UPLOADED","Uploaded"),("QUEUED","Queued"),("RUNNING","Running"),("SUCCESS","Success"),("FAILED","Failed")],default="UPLOADED",max_length=20)),
                ("execution_id",models.UUIDField(blank=True,null=True)),
                ("rows_total",models.PositiveBigIntegerField(default=0)),
                ("rows_valid",models.PositiveBigIntegerField(default=0)),
                ("rows_imported",models.PositiveBigIntegerField(default=0)),
                ("rows_failed",models.PositiveBigIntegerField(default=0)),
                ("error_report",models.JSONField(blank=True,default=list)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("finished_at",models.DateTimeField(blank=True,null=True)),
                ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="import_jobs_created",to=settings.AUTH_USER_MODEL)),
                ("target_table",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="import_jobs",to="data_model.tableasset")),
                ("workspace",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="import_jobs",to="workspaces.workspace")),
            ],
            options={"ordering":["-created_at"]},
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("file_type",models.CharField(choices=[("CSV","CSV"),("XLSX","Excel")],max_length=10)),
                ("columns",models.JSONField(blank=True,default=list)),
                ("filters",models.JSONField(blank=True,default=list)),
                ("row_limit",models.PositiveBigIntegerField(default=100000)),
                ("output_file",models.FileField(blank=True,upload_to="exports/%Y/%m/%d/")),
                ("status",models.CharField(choices=[("QUEUED","Queued"),("RUNNING","Running"),("SUCCESS","Success"),("FAILED","Failed")],default="QUEUED",max_length=20)),
                ("execution_id",models.UUIDField(blank=True,null=True)),
                ("rows_exported",models.PositiveBigIntegerField(default=0)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("finished_at",models.DateTimeField(blank=True,null=True)),
                ("error_message",models.TextField(blank=True)),
                ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="export_jobs_created",to=settings.AUTH_USER_MODEL)),
                ("source_table",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="export_jobs",to="data_model.tableasset")),
                ("workspace",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="export_jobs",to="workspaces.workspace")),
            ],
            options={"ordering":["-created_at"]},
        ),
    ]
