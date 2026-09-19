import uuid
from django.conf import settings
from django.db import models
from workspaces.models import Workspace

class ScriptBlock(models.Model):
    class Language(models.TextChoices):
        SQL="SQL","SQL"; PYTHON="PYTHON","Python"; DAX="DAX","DAX"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="script_blocks")
    name=models.CharField(max_length=220)
    language=models.CharField(max_length=12,choices=Language.choices)
    # Legacy hint retained for migration compatibility; v17 derives artifacts from code.
    purpose=models.CharField(max_length=24,blank=True,default="")
    code=models.TextField()
    context=models.JSONField(default=dict,blank=True)
    linked_object_type=models.CharField(max_length=80,blank=True)
    linked_object_id=models.CharField(max_length=80,blank=True)
    status=models.CharField(max_length=20,default="SAVED")
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="script_blocks_created")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["created_at"]

class ScriptArtifact(models.Model):
    class Type(models.TextChoices):
        TRANSFORMATION="TRANSFORMATION","Transformation"; FIELD_RULE="FIELD_RULE","Field rule"; MEASURE="MEASURE","Measure"; CHART="CHART","Chart"; FUNCTION="FUNCTION","Function"; ML_MODEL="ML_MODEL","ML model"; OPTIMIZATION="OPTIMIZATION","Optimization"; DATASET="DATASET","Dataset"; VARIABLE="VARIABLE","Variable"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    script_block=models.ForeignKey(ScriptBlock,on_delete=models.CASCADE,related_name="artifacts")
    artifact_type=models.CharField(max_length=24,choices=Type.choices)
    name=models.CharField(max_length=220,blank=True)
    object_type=models.CharField(max_length=80,blank=True)
    object_id=models.CharField(max_length=80,blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class ComputeTarget(models.Model):
    class Kind(models.TextChoices): PLATFORM="PLATFORM","Platform compute"; CUSTOMER="CUSTOMER","Customer compute"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="compute_targets")
    name=models.CharField(max_length=160)
    kind=models.CharField(max_length=16,choices=Kind.choices,default=Kind.PLATFORM)
    agent_key=models.CharField(max_length=180,blank=True)
    status=models.CharField(max_length=20,default="DRAFT")
    capabilities=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class PythonEnvironment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name="python_environments")
    name=models.CharField(max_length=160)
    python_version=models.CharField(max_length=32,default="3.13")
    compute_target=models.ForeignKey(ComputeTarget,on_delete=models.PROTECT,related_name="environments")
    status=models.CharField(max_length=20,default="DRAFT")
    version=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class EnvironmentPackage(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    environment=models.ForeignKey(PythonEnvironment,on_delete=models.CASCADE,related_name="packages")
    name=models.CharField(max_length=160)
    version_spec=models.CharField(max_length=80,blank=True)
    status=models.CharField(max_length=20,default="REQUESTED")
    source=models.CharField(max_length=20,default="PYPI")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=[("environment","name")]
