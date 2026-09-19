import uuid

from django.conf import settings
from django.db import models

from data_model.models import FieldAsset, TableAsset
from datasources.models import DataAsset
from workspaces.models import Workspace


class SemanticModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="semantic_models",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    base_table = models.ForeignKey(
        TableAsset,
        on_delete=models.CASCADE,
        related_name="semantic_models",
    )
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="semantic_models_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_semantic_model_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name


class SemanticDimension(models.Model):
    class DimensionType(models.TextChoices):
        CATEGORY = "CATEGORY", "Categoría"
        DATE = "DATE", "Fecha"
        DATETIME = "DATETIME", "Fecha y hora"
        NUMBER = "NUMBER", "Número"
        TEXT = "TEXT", "Texto"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    semantic_model = models.ForeignKey(
        SemanticModel,
        on_delete=models.CASCADE,
        related_name="dimensions",
    )
    field = models.ForeignKey(
        FieldAsset,
        on_delete=models.CASCADE,
        related_name="semantic_dimensions",
    )
    name = models.CharField(max_length=180)
    dimension_type = models.CharField(
        max_length=20,
        choices=DimensionType.choices,
        default=DimensionType.CATEGORY,
    )
    format = models.CharField(max_length=120, blank=True)
    hierarchy = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["semantic_model", "name"],
                name="unique_dimension_name_per_semantic_model",
            )
        ]

    def __str__(self):
        return f"{self.semantic_model.name} / {self.name}"


class MetricDefinition(models.Model):
    class ExpressionType(models.TextChoices):
        SIMPLE = "SIMPLE", "Simple"
        SQL = "SQL", "SQL"
        DAX = "DAX", "DAX"
        PYTHON = "PYTHON", "Python"

    class Aggregation(models.TextChoices):
        SUM = "SUM", "Suma"
        AVG = "AVG", "Promedio"
        MIN = "MIN", "Mínimo"
        MAX = "MAX", "Máximo"
        COUNT = "COUNT", "Conteo"
        COUNT_DISTINCT = "COUNT_DISTINCT", "Conteo distinto"
        NONE = "NONE", "Sin agregación"

    class FormatType(models.TextChoices):
        NUMBER = "NUMBER", "Número"
        INTEGER = "INTEGER", "Entero"
        PERCENT = "PERCENT", "Porcentaje"
        CURRENCY = "CURRENCY", "Moneda"
        DURATION = "DURATION", "Duración"
        CUSTOM = "CUSTOM", "Personalizado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="metric_definitions",
    )
    semantic_model = models.ForeignKey(
        SemanticModel,
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)

    expression_type = models.CharField(
        max_length=20,
        choices=ExpressionType.choices,
        default=ExpressionType.SIMPLE,
    )
    source_field = models.ForeignKey(
        FieldAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metrics",
    )
    aggregation = models.CharField(
        max_length=30,
        choices=Aggregation.choices,
        default=Aggregation.SUM,
    )

    # SQL expression only, not a full statement.
    expression = models.TextField(blank=True)

    format_type = models.CharField(
        max_length=20,
        choices=FormatType.choices,
        default=FormatType.NUMBER,
    )
    unit = models.CharField(max_length=40, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)

    enabled = models.BooleanField(default=True)
    cache_ttl_seconds = models.PositiveIntegerField(default=60)

    data_asset = models.OneToOneField(
        DataAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metric_definition",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="metrics_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_metric_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name
