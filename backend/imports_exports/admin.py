from django.contrib import admin
from .models import ExportJob, ImportJob, SourceSyncPolicy


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ["id", "workspace", "target_table", "target_table_name", "file_type", "mode", "status", "rows_imported", "created_at"]
    list_filter = ["file_type", "mode", "status"]


@admin.register(SourceSyncPolicy)
class SourceSyncPolicyAdmin(admin.ModelAdmin):
    list_display = ["id", "workspace", "source_data_source", "source_table", "target_table_name", "strategy", "schedule", "status", "last_sync_at"]
    list_filter = ["strategy", "schedule", "status", "enabled"]


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ["id", "workspace", "source_table", "file_type", "status", "rows_exported", "created_at"]
    list_filter = ["file_type", "status"]
