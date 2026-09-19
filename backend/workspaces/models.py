import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        SUSPENDED = "SUSPENDED", "Suspendida"
        ARCHIVED = "ARCHIVED", "Archivada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organizations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Propietario"
        ADMIN = "ADMIN", "Administrador"
        BUILDER = "BUILDER", "Constructor"
        ANALYST = "ANALYST", "Analista"
        VIEWER = "VIEWER", "Visualizador"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_membership_per_organization_user",
            )
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"


class Workspace(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        ARCHIVED = "ARCHIVED", "Archivado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="workspaces",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workspaces_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_workspace_slug_per_organization",
            )
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"
