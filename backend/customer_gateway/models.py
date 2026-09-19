import uuid
from django.conf import settings
from django.db import models
from workspaces.models import Workspace
from datasources.models import DataSource

class GatewayRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING="PENDING","Pending enrollment"
        ONLINE="ONLINE","Online"
        OFFLINE="OFFLINE","Offline"
        REVOKED="REVOKED","Revoked"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="gateways")
    name=models.CharField(max_length=180)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    enrollment_code_hash=models.CharField(max_length=64,blank=True)
    enrollment_expires_at=models.DateTimeField(null=True,blank=True)
    agent_token_hash=models.CharField(max_length=64,blank=True)
    token_version=models.PositiveIntegerField(default=0)
    agent_version=models.CharField(max_length=80,blank=True)
    platform=models.CharField(max_length=120,blank=True)
    hostname=models.CharField(max_length=255,blank=True)
    last_seen_at=models.DateTimeField(null=True,blank=True)
    last_ip=models.GenericIPAddressField(null=True,blank=True)
    capabilities=models.JSONField(default=dict,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="gateways_created")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["name"]
        constraints=[models.UniqueConstraint(fields=["workspace","name"],name="unique_gateway_name_per_workspace")]

class GatewayDataSourceBinding(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    gateway=models.ForeignKey(GatewayRegistration,on_delete=models.CASCADE,related_name="bindings")
    data_source=models.OneToOneField(DataSource,on_delete=models.CASCADE,related_name="gateway_binding")
    local_connection_name=models.CharField(max_length=180)
    enabled=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["gateway","local_connection_name"],name="unique_gateway_local_connection_name")]

class GatewayHeartbeat(models.Model):
    id=models.BigAutoField(primary_key=True)
    gateway=models.ForeignKey(GatewayRegistration,on_delete=models.CASCADE,related_name="heartbeats")
    agent_version=models.CharField(max_length=80,blank=True)
    metrics=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]

class GatewayJob(models.Model):
    class Operation(models.TextChoices):
        TEST_CONNECTION="TEST_CONNECTION","Test connection"
        CATALOG="CATALOG","Catalog introspection"
        READ_PAGE="READ_PAGE","Read page"
        QUERY_PLAN="QUERY_PLAN","Operational query plan"
        INSERT="INSERT","Insert"
        UPDATE="UPDATE","Update"
        DELETE="DELETE","Delete"
    class Status(models.TextChoices):
        QUEUED="QUEUED","Queued"
        CLAIMED="CLAIMED","Claimed"
        SUCCESS="SUCCESS","Success"
        FAILED="FAILED","Failed"
        CANCELLED="CANCELLED","Cancelled"
        EXPIRED="EXPIRED","Expired"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    gateway=models.ForeignKey(GatewayRegistration,on_delete=models.CASCADE,related_name="jobs")
    data_source=models.ForeignKey(DataSource,on_delete=models.CASCADE,related_name="gateway_jobs")
    operation=models.CharField(max_length=30,choices=Operation.choices)
    payload=models.JSONField(default=dict,blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.QUEUED)
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="gateway_jobs_requested")
    claimed_at=models.DateTimeField(null=True,blank=True)
    lease_expires_at=models.DateTimeField(null=True,blank=True)
    finished_at=models.DateTimeField(null=True,blank=True)
    result=models.JSONField(default=dict,blank=True)
    error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["created_at"]
        indexes=[models.Index(fields=["gateway","status","created_at"])]

class GatewayImportRequest(models.Model):
    class Scope(models.TextChoices):
        ENTIRE_DATABASE="ENTIRE_DATABASE","Entire database"
        SELECTED_TABLES="SELECTED_TABLES","Selected tables"
    class Status(models.TextChoices):
        PENDING="PENDING","Pending"
        DISCOVERING="DISCOVERING","Discovering"
        IMPORTING="IMPORTING","Importing"
        SUCCEEDED="SUCCEEDED","Succeeded"
        FAILED="FAILED","Failed"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="gateway_import_requests")
    data_source=models.ForeignKey(DataSource,on_delete=models.CASCADE,related_name="gateway_import_requests")
    scope=models.CharField(max_length=30,choices=Scope.choices,default=Scope.ENTIRE_DATABASE)
    selected_tables=models.JSONField(default=list,blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING)
    progress=models.PositiveSmallIntegerField(default=0)
    table_progress=models.JSONField(default=dict,blank=True)
    catalog_job=models.ForeignKey(GatewayJob,on_delete=models.SET_NULL,null=True,blank=True,related_name="import_requests")
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="gateway_import_requests")
    error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["-created_at"]
