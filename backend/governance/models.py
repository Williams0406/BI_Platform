import uuid
from django.conf import settings
from django.db import models
from workspaces.models import Workspace
from datasources.models import DataSource

class AuditLog(models.Model):
    id=models.BigAutoField(primary_key=True)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="audit_logs")
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_logs")
    action=models.CharField(max_length=80)
    resource_type=models.CharField(max_length=80)
    resource_id=models.CharField(max_length=180,blank=True)
    detail=models.JSONField(default=dict,blank=True)
    ip_address=models.GenericIPAddressField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["-created_at"]
        indexes=[models.Index(fields=["workspace","created_at"]),models.Index(fields=["resource_type","resource_id"])]

class WorkspaceQuota(models.Model):
    workspace=models.OneToOneField(Workspace,on_delete=models.CASCADE,primary_key=True,related_name="quota")
    max_storage_mb=models.PositiveBigIntegerField(default=10240)
    max_import_rows=models.PositiveBigIntegerField(default=500000)
    max_export_rows=models.PositiveBigIntegerField(default=500000)
    max_concurrent_jobs=models.PositiveIntegerField(default=4)
    max_python_runtime_seconds=models.PositiveIntegerField(default=300)
    max_optimization_seconds=models.PositiveIntegerField(default=1800)
    updated_at=models.DateTimeField(auto_now=True)

class WorkspaceUsage(models.Model):
    workspace=models.OneToOneField(Workspace,on_delete=models.CASCADE,primary_key=True,related_name="usage")
    storage_bytes=models.PositiveBigIntegerField(default=0)
    import_rows=models.PositiveBigIntegerField(default=0)
    export_rows=models.PositiveBigIntegerField(default=0)
    executions_started=models.PositiveBigIntegerField(default=0)
    updated_at=models.DateTimeField(auto_now=True)

class ResourcePermission(models.Model):
    class Effect(models.TextChoices):
        ALLOW="ALLOW","Allow"
        DENY="DENY","Deny"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="resource_permissions")
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="resource_permissions")
    resource_type=models.CharField(max_length=40)
    resource_id=models.CharField(max_length=180,blank=True)
    field_name=models.CharField(max_length=180,blank=True)
    action=models.CharField(max_length=40)
    effect=models.CharField(max_length=10,choices=Effect.choices,default=Effect.ALLOW)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["workspace","user","resource_type","resource_id","field_name","action"],name="unique_resource_permission")]

class EncryptedSecret(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="encrypted_secrets")
    data_source=models.OneToOneField(DataSource,on_delete=models.CASCADE,null=True,blank=True,related_name="encrypted_secret")
    name=models.CharField(max_length=180)
    ciphertext=models.BinaryField()
    key_version=models.PositiveIntegerField(default=1)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="encrypted_secrets_created")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["workspace","name"],name="unique_secret_name_per_workspace")]

class DestructiveChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING="PENDING","Pending"
        APPROVED="APPROVED","Approved"
        EXECUTED="EXECUTED","Executed"
        REJECTED="REJECTED","Rejected"
        EXPIRED="EXPIRED","Expired"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="destructive_change_requests")
    action=models.CharField(max_length=80)
    resource_type=models.CharField(max_length=80)
    resource_id=models.CharField(max_length=180)
    reason=models.TextField(blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="destructive_requests_created")
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="destructive_requests_approved")
    expires_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    approved_at=models.DateTimeField(null=True,blank=True)
    executed_at=models.DateTimeField(null=True,blank=True)

class RetentionPolicy(models.Model):
    workspace=models.OneToOneField(Workspace,on_delete=models.CASCADE,primary_key=True,related_name="retention_policy")
    audit_log_days=models.PositiveIntegerField(default=365)
    execution_log_days=models.PositiveIntegerField(default=180)
    export_artifact_days=models.PositiveIntegerField(default=30)
    import_artifact_days=models.PositiveIntegerField(default=30)
    updated_at=models.DateTimeField(auto_now=True)

class WorkspacePolicy(models.Model):
    workspace=models.OneToOneField(Workspace,on_delete=models.CASCADE,primary_key=True,related_name="governance_policy")
    allow_import=models.BooleanField(default=True)
    allow_refresh=models.BooleanField(default=True)
    allow_external_write=models.BooleanField(default=False)
    allow_schema_changes=models.BooleanField(default=False)
    allow_operational_writeback=models.BooleanField(default=False)
    allow_delete=models.BooleanField(default=False)
    allow_platform_compute=models.BooleanField(default=True)
    allow_customer_compute=models.BooleanField(default=True)
    allow_customer_packages=models.BooleanField(default=True)
    require_ddl_approval=models.BooleanField(default=True)
    require_bulk_write_approval=models.BooleanField(default=True)
    updated_at=models.DateTimeField(auto_now=True)

class DataCopyEvent(models.Model):
    """Immutable timeline of a source's editable Platform copy."""
    class Kind(models.TextChoices):
        INITIAL_SNAPSHOT="INITIAL_SNAPSHOT","Initial snapshot"
        REFRESH="REFRESH","Refresh"
        TRANSFORMATION="TRANSFORMATION","Transformation"
        DATA_CHANGE="DATA_CHANGE","Data change"
        SCHEMA_CHANGE="SCHEMA_CHANGE","Schema change"
        RELATIONSHIP="RELATIONSHIP","Relationship"
        VERSION="VERSION","Version"
        PUBLISH="PUBLISH","Publish"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="data_copy_events")
    source=models.ForeignKey(DataSource,on_delete=models.CASCADE,related_name="copy_events")
    binding=models.ForeignKey("datasources.SourceBinding",on_delete=models.SET_NULL,null=True,blank=True,related_name="copy_events")
    kind=models.CharField(max_length=30,choices=Kind.choices)
    title=models.CharField(max_length=180)
    summary=models.TextField(blank=True)
    detail=models.JSONField(default=dict,blank=True)
    version=models.PositiveBigIntegerField(default=1)
    published=models.BooleanField(default=False)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="data_copy_events")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["created_at"]
        indexes=[models.Index(fields=["workspace","source","created_at"])]
