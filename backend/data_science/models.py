import uuid
from django.conf import settings
from django.db import models
from data_model.models import FieldAsset, TableAsset
from datasources.models import DataAsset
from workspaces.models import Workspace

class PythonTransformation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="python_transformations")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    code = models.TextField(help_text="Use table('alias') y save_table(dataframe).")
    output_name = models.CharField(max_length=180)
    output_asset = models.OneToOneField(DataAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name="producer_python_transformation")
    allowed_packages = models.JSONField(default=list, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=300)
    memory_limit_mb = models.PositiveIntegerField(default=1024)
    max_input_rows = models.PositiveIntegerField(default=100000)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="python_transformations_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["workspace", "name"], name="unique_python_transformation_name_per_workspace")]
    def __str__(self): return self.name

class PythonTransformationInput(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transformation = models.ForeignKey(PythonTransformation, on_delete=models.CASCADE, related_name="inputs")
    asset = models.ForeignKey(DataAsset, on_delete=models.CASCADE, related_name="python_transformation_inputs")
    alias = models.CharField(max_length=80)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transformation", "alias"], name="unique_python_input_alias"),
            models.UniqueConstraint(fields=["transformation", "asset"], name="unique_python_input_asset"),
        ]

class DatasetDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="datasets")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    source_table = models.ForeignKey(TableAsset, on_delete=models.CASCADE, related_name="dataset_definitions")
    filter_config = models.JSONField(default=list, blank=True)
    sample_limit = models.PositiveIntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="datasets_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["workspace", "name"], name="unique_dataset_name_per_workspace")]
    def __str__(self): return self.name

class ModelDefinition(models.Model):
    class TaskType(models.TextChoices):
        CLASSIFICATION = "CLASSIFICATION", "Clasificación"
        REGRESSION = "REGRESSION", "Regresión"
    class Algorithm(models.TextChoices):
        LOGISTIC_REGRESSION = "LOGISTIC_REGRESSION", "Logistic Regression"
        RANDOM_FOREST_CLASSIFIER = "RANDOM_FOREST_CLASSIFIER", "Random Forest Classifier"
        LINEAR_REGRESSION = "LINEAR_REGRESSION", "Linear Regression"
        RANDOM_FOREST_REGRESSOR = "RANDOM_FOREST_REGRESSOR", "Random Forest Regressor"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="ml_models")
    dataset = models.ForeignKey(DatasetDefinition, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    algorithm = models.CharField(max_length=40, choices=Algorithm.choices)
    features = models.ManyToManyField(FieldAsset, related_name="ml_feature_models")
    target = models.ForeignKey(FieldAsset, on_delete=models.PROTECT, related_name="ml_target_models")
    parameters = models.JSONField(default=dict, blank=True)
    test_size = models.FloatField(default=0.2)
    random_state = models.IntegerField(default=42)
    enabled = models.BooleanField(default=True)
    data_asset = models.OneToOneField(DataAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name="ml_model_definition")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ml_models_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["workspace", "name"], name="unique_ml_model_name_per_workspace")]
    def __str__(self): return self.name

class ModelRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "En cola"
        RUNNING = "RUNNING", "Ejecutando"
        SUCCESS = "SUCCESS", "Exitosa"
        FAILED = "FAILED", "Fallida"
        CANCELLED = "CANCELLED", "Cancelada"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="runs")
    execution_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    metrics = models.JSONField(default=dict, blank=True)
    parameters_snapshot = models.JSONField(default=dict, blank=True)
    input_asset_versions = models.JSONField(default=dict, blank=True)
    row_count = models.PositiveBigIntegerField(default=0)
    train_row_count = models.PositiveBigIntegerField(default=0)
    test_row_count = models.PositiveBigIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]

class ModelVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="versions")
    run = models.OneToOneField(ModelRun, on_delete=models.CASCADE, related_name="model_version")
    version = models.PositiveIntegerField()
    artifact_path = models.TextField()
    metrics = models.JSONField(default=dict, blank=True)
    feature_names = models.JSONField(default=list, blank=True)
    target_name = models.CharField(max_length=180)
    algorithm = models.CharField(max_length=80)
    sklearn_version = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["model", "version"], name="unique_model_version_number")]

class PredictionAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name="prediction_assets")
    source_dataset = models.ForeignKey(DatasetDefinition, on_delete=models.CASCADE, related_name="predictions")
    data_asset = models.OneToOneField(DataAsset, on_delete=models.CASCADE, related_name="prediction_definition")
    artifact_path = models.TextField()
    row_count = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
