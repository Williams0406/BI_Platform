import uuid
from django.conf import settings
from django.db import models
from data_model.models import TableAsset
from datasources.models import DataSource
from workspaces.models import Workspace


class ImportJob(models.Model):
    class FileType(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "Excel"

    class Mode(models.TextChoices):
        CREATE = "CREATE", "Create new table"
        APPEND = "APPEND", "Append"
        REPLACE = "REPLACE", "Replace"
        UPSERT = "UPSERT", "Upsert"

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="import_jobs")
    target_table = models.ForeignKey(
        TableAsset,
        on_delete=models.CASCADE,
        related_name="import_jobs",
        null=True,
        blank=True,
    )
    target_table_name = models.CharField(max_length=63, blank=True)
    target_display_name = models.CharField(max_length=180, blank=True)
    file = models.FileField(upload_to="imports/%Y/%m/%d/")
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    sheet_name = models.CharField(max_length=180, blank=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CREATE)
    column_mapping = models.JSONField(default=dict, blank=True)
    inferred_schema = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    execution_id = models.UUIDField(null=True, blank=True)
    rows_total = models.PositiveBigIntegerField(default=0)
    rows_valid = models.PositiveBigIntegerField(default=0)
    rows_imported = models.PositiveBigIntegerField(default=0)
    rows_failed = models.PositiveBigIntegerField(default=0)
    error_report = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="import_jobs_created")
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class SourceSyncPolicy(models.Model):
    class Strategy(models.TextChoices):
        FULL = "FULL", "Full refresh"
        INCREMENTAL = "INCREMENTAL", "Incremental refresh"

    class Schedule(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        HOURLY = "HOURLY", "Hourly"
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        CUSTOM = "CUSTOM", "Custom"

    class Status(models.TextChoices):
        IDLE = "IDLE", "Idle"
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="source_sync_policies")
    source_data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="sync_policies")
    source_table = models.ForeignKey(TableAsset, on_delete=models.CASCADE, related_name="source_sync_policies")
    target_table = models.ForeignKey(
        TableAsset,
        on_delete=models.SET_NULL,
        related_name="target_sync_policies",
        null=True,
        blank=True,
    )
    target_table_name = models.CharField(max_length=63)
    target_display_name = models.CharField(max_length=180, blank=True)
    strategy = models.CharField(max_length=20, choices=Strategy.choices, default=Strategy.FULL)
    schedule = models.CharField(max_length=20, choices=Schedule.choices, default=Schedule.MANUAL)
    custom_interval_minutes = models.PositiveIntegerField(default=60)
    incremental_field = models.CharField(max_length=180, blank=True)
    last_cursor_value = models.JSONField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDLE)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_rows = models.PositiveBigIntegerField(default=0)
    last_error = models.TextField(blank=True)
    execution_id = models.UUIDField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="source_sync_policies_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_data_source__name", "source_table__schema_name", "source_table__table_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_table", "target_table_name"],
                name="unique_source_table_sync_target_name",
            )
        ]


class ExportJob(models.Model):
    class FileType(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "Excel"

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="export_jobs")
    source_table = models.ForeignKey(TableAsset, on_delete=models.CASCADE, related_name="export_jobs")
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    columns = models.JSONField(default=list, blank=True)
    filters = models.JSONField(default=list, blank=True)
    row_limit = models.PositiveBigIntegerField(default=100000)
    output_file = models.FileField(upload_to="exports/%Y/%m/%d/", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    execution_id = models.UUIDField(null=True, blank=True)
    rows_exported = models.PositiveBigIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="export_jobs_created")
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
