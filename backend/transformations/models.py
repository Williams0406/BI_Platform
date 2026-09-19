import uuid

from django.conf import settings
from django.db import models

from datasources.models import DataAsset
from workspaces.models import Workspace


class SQLTransformation(models.Model):
    class OutputMode(models.TextChoices):
        VIEW = "VIEW", "Vista"
        TABLE = "TABLE", "Tabla materializada"

    class RefreshPolicy(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTO = "AUTO", "Automática"
        SCHEDULED = "SCHEDULED", "Programada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="sql_transformations",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)

    sql = models.TextField(
        help_text="Solo SELECT/WITH. Use {{asset:<uuid>}} para referenciar Data Assets."
    )

    output_mode = models.CharField(
        max_length=20,
        choices=OutputMode.choices,
        default=OutputMode.VIEW,
    )
    output_asset = models.OneToOneField(
        DataAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="producer_sql_transformation",
    )

    refresh_policy = models.CharField(
        max_length=20,
        choices=RefreshPolicy.choices,
        default=RefreshPolicy.MANUAL,
    )
    enabled = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sql_transformations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_sql_transformation_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name


class TransformationInput(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transformation = models.ForeignKey(
        SQLTransformation,
        on_delete=models.CASCADE,
        related_name="inputs",
    )
    asset = models.ForeignKey(
        DataAsset,
        on_delete=models.CASCADE,
        related_name="sql_transformation_inputs",
    )
    alias = models.CharField(max_length=120, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["transformation", "asset"],
                name="unique_transformation_input_asset",
            )
        ]
