import uuid

from django.conf import settings
from django.db import models

from datasources.models import DataAsset
from workspaces.models import Workspace


class AssetState(models.Model):
    class Status(models.TextChoices):
        FRESH = "FRESH", "Actualizado"
        STALE = "STALE", "Desactualizado"
        RUNNING = "RUNNING", "Ejecutando"
        FAILED = "FAILED", "Fallido"
        BLOCKED = "BLOCKED", "Bloqueado"
        ARCHIVED = "ARCHIVED", "Archivado"

    asset = models.OneToOneField(
        DataAsset,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="dependency_state",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FRESH,
    )
    version = models.PositiveBigIntegerField(default=1)
    last_changed_at = models.DateTimeField(auto_now=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.asset.name}: {self.status}@{self.version}"


class AssetDependency(models.Model):
    class DependencyType(models.TextChoices):
        DATA = "DATA", "Datos"
        CALCULATION = "CALCULATION", "Cálculo"
        MODEL_INPUT = "MODEL_INPUT", "Input de modelo"
        VISUALIZATION = "VISUALIZATION", "Visualización"

    class RefreshPolicy(models.TextChoices):
        AUTO = "AUTO", "Automática"
        MARK_STALE = "MARK_STALE", "Marcar desactualizado"
        MANUAL = "MANUAL", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="asset_dependencies",
    )
    upstream = models.ForeignKey(
        DataAsset,
        on_delete=models.CASCADE,
        related_name="downstream_dependencies",
    )
    downstream = models.ForeignKey(
        DataAsset,
        on_delete=models.CASCADE,
        related_name="upstream_dependencies",
    )
    dependency_type = models.CharField(
        max_length=30,
        choices=DependencyType.choices,
        default=DependencyType.DATA,
    )
    refresh_policy = models.CharField(
        max_length=20,
        choices=RefreshPolicy.choices,
        default=RefreshPolicy.MARK_STALE,
    )
    active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["upstream", "downstream"],
                name="unique_asset_dependency_edge",
            ),
            models.CheckConstraint(
                condition=~models.Q(upstream=models.F("downstream")),
                name="dependency_no_self_loop",
            ),
        ]

    def __str__(self):
        return f"{self.upstream.name} -> {self.downstream.name}"


class ChangeEvent(models.Model):
    class ChangeType(models.TextChoices):
        INSERT = "INSERT", "Insert"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        REFRESH = "REFRESH", "Refresh"
        STRUCTURE = "STRUCTURE", "Structure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="change_events",
    )
    asset = models.ForeignKey(
        DataAsset,
        on_delete=models.CASCADE,
        related_name="change_events",
    )
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    record_key = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_events_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    propagated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
