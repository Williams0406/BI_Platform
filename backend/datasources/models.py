import uuid

from django.conf import settings
from django.db import models

from workspaces.models import Workspace


class DataSource(models.Model):
    class Mode(models.TextChoices):
        MANAGED = "MANAGED", "Administrada por la plataforma"
        EXTERNAL = "EXTERNAL", "Base externa"
        PRIVATE_GATEWAY = "PRIVATE_GATEWAY", "Gateway privado"

    class Engine(models.TextChoices):
        PLATFORM_POSTGRES = "PLATFORM_POSTGRES", "PostgreSQL administrado"
        POSTGRESQL = "POSTGRESQL", "PostgreSQL"
        SQLSERVER = "SQLSERVER", "Microsoft SQL Server"
        OTHER = "OTHER", "Otro"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        ACTIVE = "ACTIVE", "Activa"
        UNAVAILABLE = "UNAVAILABLE", "No disponible"
        ARCHIVED = "ARCHIVED", "Archivada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="data_sources",
    )
    name = models.CharField(max_length=180)
    mode = models.CharField(max_length=30, choices=Mode.choices)
    engine = models.CharField(max_length=40, choices=Engine.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)
    can_ddl = models.BooleanField(default=False)

    # Solo metadatos no sensibles. Credenciales reales se implementarán
    # en la fase de connectors/governance.
    connection_metadata = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="data_sources_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_datasource_name_per_workspace",
            )
        ]

    def __str__(self):
        return f"{self.workspace} / {self.name}"


class DataAsset(models.Model):
    class AssetType(models.TextChoices):
        TABLE = "TABLE", "Tabla"
        VIEW = "VIEW", "Vista"
        DERIVED_TABLE = "DERIVED_TABLE", "Tabla derivada"
        DATASET = "DATASET", "Dataset"
        METRIC = "METRIC", "Métrica"
        CHART = "CHART", "Gráfico"
        DASHBOARD = "DASHBOARD", "Dashboard"
        REPORT = "REPORT", "Reporte"
        ML_MODEL = "ML_MODEL", "Modelo ML"
        OPTIMIZATION_MODEL = "OPTIMIZATION_MODEL", "Modelo de optimización"
        OTHER = "OTHER", "Otro"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        STALE = "STALE", "Desactualizado"
        ARCHIVED = "ARCHIVED", "Archivado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="data_assets",
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    name = models.CharField(max_length=180)
    asset_type = models.CharField(max_length=40, choices=AssetType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    physical_schema = models.CharField(max_length=180, blank=True)
    physical_name = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    version = models.PositiveBigIntegerField(default=1)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="data_assets_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name", "asset_type"],
                name="unique_asset_name_type_per_workspace",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.asset_type})"

class SourceBinding(models.Model):
    """Maps a source table to its editable Platform copy."""
    class AccessMode(models.TextChoices):
        LIVE = "LIVE", "Live"
        IMPORTED = "IMPORTED", "Platform copy"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="source_bindings")
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="platform_bindings")
    source_schema = models.CharField(max_length=180, blank=True)
    source_table = models.CharField(max_length=180)
    platform_asset = models.ForeignKey(DataAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="source_bindings")
    access_mode = models.CharField(max_length=20, choices=AccessMode.choices, default=AccessMode.IMPORTED)
    primary_key_fields = models.JSONField(default=list, blank=True)
    cursor_field = models.CharField(max_length=180, blank=True)
    last_refresh_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="source_bindings_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_table"]
        constraints = [models.UniqueConstraint(fields=["source", "source_schema", "source_table"], name="unique_source_table_binding")]


class PublishPlan(models.Model):
    """Reviewed Platform -> Source deployment plan. Never executes implicitly."""
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REVIEWED = "REVIEWED", "Reviewed"
        APPROVED = "APPROVED", "Approved"
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Scope(models.TextChoices):
        SCHEMA = "SCHEMA", "Schema"
        DATA = "DATA", "Data"
        SCHEMA_DATA = "SCHEMA_DATA", "Schema + data"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="publish_plans")
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="publish_plans")
    binding = models.ForeignKey(SourceBinding, null=True, blank=True, on_delete=models.SET_NULL, related_name="publish_plans")
    name = models.CharField(max_length=180)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.DATA)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    schema_changes = models.JSONField(default=list, blank=True)
    data_changes = models.JSONField(default=dict, blank=True)
    generated_sql = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="publish_plans_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class WritebackPolicy(models.Model):
    """Allow-list used by Operational Views before source mutations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="writeback_policies")
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="writeback_policies")
    source_schema = models.CharField(max_length=180, blank=True)
    source_table = models.CharField(max_length=180)
    allowed_operations = models.JSONField(default=list, blank=True)
    allowed_fields = models.JSONField(default=list, blank=True)
    key_fields = models.JSONField(default=list, blank=True)
    validation_rules = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="writeback_policies_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_table"]
        constraints = [models.UniqueConstraint(fields=["source", "source_schema", "source_table"], name="unique_writeback_policy_per_source_table")]
