from django.contrib import admin
from .models import AuditLog,DestructiveChangeRequest,EncryptedSecret,ResourcePermission,RetentionPolicy,WorkspaceQuota,WorkspaceUsage

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display=["workspace","action","resource_type","resource_id","actor","created_at"]
    list_filter=["action","resource_type"];search_fields=["resource_id","actor__email"]
    readonly_fields=["workspace","actor","action","resource_type","resource_id","detail","ip_address","created_at"]

@admin.register(WorkspaceQuota)
class WorkspaceQuotaAdmin(admin.ModelAdmin):
    list_display=["workspace","max_import_rows","max_export_rows","max_concurrent_jobs","max_storage_mb"]

@admin.register(WorkspaceUsage)
class WorkspaceUsageAdmin(admin.ModelAdmin):
    list_display=["workspace","storage_bytes","import_rows","export_rows","executions_started"]

@admin.register(ResourcePermission)
class ResourcePermissionAdmin(admin.ModelAdmin):
    list_display=["workspace","user","resource_type","resource_id","field_name","action","effect"]
    list_filter=["resource_type","action","effect"]

@admin.register(EncryptedSecret)
class EncryptedSecretAdmin(admin.ModelAdmin):
    list_display=["workspace","name","data_source","key_version","updated_at"]
    exclude=["ciphertext"]

@admin.register(DestructiveChangeRequest)
class DestructiveChangeRequestAdmin(admin.ModelAdmin):
    list_display=["workspace","action","resource_type","resource_id","status","requested_by","approved_by","created_at"]
    list_filter=["status","action"]

@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(admin.ModelAdmin):
    list_display=["workspace","audit_log_days","execution_log_days","export_artifact_days","import_artifact_days"]
