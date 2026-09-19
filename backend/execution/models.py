import uuid

from django.conf import settings
from django.db import models

from workspaces.models import Workspace


class Execution(models.Model):
    class ObjectType(models.TextChoices):
        SQL_TRANSFORMATION = "SQL_TRANSFORMATION", "Transformación SQL"
        PYTHON_TRANSFORMATION = "PYTHON_TRANSFORMATION", "Transformación Python"
        ML_TRAINING = "ML_TRAINING", "Entrenamiento ML"
        ML_INFERENCE = "ML_INFERENCE", "Inferencia ML"
        OPTIMIZATION = "OPTIMIZATION", "Optimización"
        IMPORT = "IMPORT", "Importación"
        EXPORT = "EXPORT", "Exportación"
        DEPENDENCY_PROPAGATION = "DEPENDENCY_PROPAGATION", "Propagación de dependencias"
        GENERIC = "GENERIC", "Genérica"

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "En cola"
        RUNNING = "RUNNING", "Ejecutando"
        SUCCESS = "SUCCESS", "Exitosa"
        FAILED = "FAILED", "Fallida"
        CANCELLED = "CANCELLED", "Cancelada"
        BLOCKED = "BLOCKED", "Bloqueada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="executions",
    )

    object_type = models.CharField(max_length=50, choices=ObjectType.choices)
    object_id = models.UUIDField(null=True, blank=True)

    queue = models.CharField(max_length=40, default="fast")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )

    progress = models.PositiveSmallIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions_requested",
    )

    parameters = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_type = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    duration_ms = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-queued_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.object_type}:{self.object_id} [{self.status}]"


class ExecutionLog(models.Model):
    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"

    id = models.BigAutoField(primary_key=True)
    execution = models.ForeignKey(
        Execution,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

class ExecutionEvent(models.Model):
    """Normalized UER event emitted by runtimes/adapters and consumed by reports."""
    class Family(models.TextChoices):
        EXECUTION = "EXECUTION", "Execution"
        METRIC = "METRIC", "Metric"
        ML = "ML", "Machine Learning"
        OPTIMIZATION = "OPTIMIZATION", "Optimization"
        ARTIFACT = "ARTIFACT", "Artifact"
        LOG = "LOG", "Log"

    id = models.BigAutoField(primary_key=True)
    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name="events")
    sequence = models.PositiveBigIntegerField()
    family = models.CharField(max_length=24, choices=Family.choices)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["execution", "sequence"], name="unique_execution_event_sequence")
        ]
        indexes = [
            models.Index(fields=["execution", "sequence"]),
            models.Index(fields=["event_type"]),
        ]
