import uuid

from django.conf import settings
from django.db import models

from data_model.models import FieldAsset, TableAsset
from workspaces.models import Workspace


class ViewDefinition(models.Model):
    class ViewType(models.TextChoices):
        TABLE = "TABLE", "Tabla"
        SPREADSHEET = "SPREADSHEET", "Hoja de cálculo"
        KANBAN = "KANBAN", "Kanban"
        MATRIX = "MATRIX", "Matriz"
        FORM = "FORM", "Formulario"
        CALENDAR = "CALENDAR", "Calendario"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        ARCHIVED = "ARCHIVED", "Archivada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="view_definitions",
    )
    source_table = models.ForeignKey(
        TableAsset,
        on_delete=models.CASCADE,
        related_name="views",
    )
    name = models.CharField(max_length=180)
    view_type = models.CharField(max_length=30, choices=ViewType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Visual configuration only. Data binding lives in ViewFieldBinding.
    config = models.JSONField(default=dict, blank=True)

    # Persisted default query configuration.
    default_filters = models.JSONField(default=list, blank=True)
    default_ordering = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="views_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_view_name_per_workspace",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.view_type})"


class ViewFieldBinding(models.Model):
    class BindingRole(models.TextChoices):
        DISPLAY = "DISPLAY", "Display"
        TITLE = "TITLE", "Title"
        SUBTITLE = "SUBTITLE", "Subtitle"
        STATUS = "STATUS", "Status"
        GROUP = "GROUP", "Group"
        ROW = "ROW", "Row"
        COLUMN = "COLUMN", "Column"
        VALUE = "VALUE", "Value"
        START_DATE = "START_DATE", "Start date"
        END_DATE = "END_DATE", "End date"
        LABEL = "LABEL", "Label"
        COLOR = "COLOR", "Color"
        SORT = "SORT", "Sort"
        HIDDEN = "HIDDEN", "Hidden"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    view = models.ForeignKey(
        ViewDefinition,
        on_delete=models.CASCADE,
        related_name="bindings",
    )
    field = models.ForeignKey(
        FieldAsset,
        on_delete=models.CASCADE,
        related_name="view_bindings",
    )
    role = models.CharField(max_length=30, choices=BindingRole.choices)
    alias = models.CharField(max_length=180, blank=True)
    editable = models.BooleanField(default=False)
    required = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    options = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["position", "role", "field__ordinal_position"]
        constraints = [
            models.UniqueConstraint(
                fields=["view", "field", "role"],
                name="unique_view_field_role_binding",
            )
        ]

    def __str__(self):
        return f"{self.view} / {self.role} -> {self.field.name}"


class ViewActionRule(models.Model):
    class ActionType(models.TextChoices):
        UPDATE_FIELD = "UPDATE_FIELD", "Actualizar campo"
        MOVE_KANBAN = "MOVE_KANBAN", "Mover tarjeta Kanban"
        EDIT_CELL = "EDIT_CELL", "Editar celda"
        RESIZE_CALENDAR = "RESIZE_CALENDAR", "Cambiar fecha/rango"
        SUBMIT_FORM = "SUBMIT_FORM", "Enviar formulario"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    view = models.ForeignKey(
        ViewDefinition,
        on_delete=models.CASCADE,
        related_name="action_rules",
    )
    name = models.CharField(max_length=180)
    action_type = models.CharField(max_length=40, choices=ActionType.choices)
    enabled = models.BooleanField(default=True)

    # Rules such as source role, target role, value mapping, validation, etc.
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.view} / {self.name}"
