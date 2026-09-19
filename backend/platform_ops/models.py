import uuid
from django.db import models
from workspaces.models import Workspace

class WorkspacePlacement(models.Model):
    workspace = models.OneToOneField(
        Workspace, on_delete=models.CASCADE, primary_key=True, related_name="placement"
    )
    database_cluster = models.CharField(max_length=120, default="primary")
    compute_pool = models.CharField(max_length=120, default="default")
    storage_prefix = models.CharField(max_length=255, blank=True)
    region = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class OperationalMetricSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    captured_at = models.DateTimeField(auto_now_add=True)
    api = models.JSONField(default=dict, blank=True)
    database = models.JSONField(default=dict, blank=True)
    executions = models.JSONField(default=dict, blank=True)
    gateways = models.JSONField(default=dict, blank=True)
    storage = models.JSONField(default=dict, blank=True)
    class Meta:
        ordering = ["-captured_at"]
