import uuid

from django.conf import settings
from django.db import models

from datasources.models import DataAsset, DataSource


class TableAsset(models.Model):
    class ObjectType(models.TextChoices):
        TABLE = "TABLE", "Tabla"
        VIEW = "VIEW", "Vista"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_asset = models.OneToOneField(DataAsset, on_delete=models.CASCADE, related_name="table_definition")
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="table_assets")
    schema_name = models.CharField(max_length=180)
    table_name = models.CharField(max_length=180)
    technical_name = models.CharField(max_length=180, blank=True, db_index=True)
    object_type = models.CharField(max_length=10, choices=ObjectType.choices, default=ObjectType.TABLE)
    primary_key_columns = models.JSONField(default=list, blank=True)
    row_version_column = models.CharField(max_length=180, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["schema_name", "table_name"]
        constraints = [models.UniqueConstraint(fields=["data_source", "schema_name", "table_name"], name="unique_catalog_table_per_source")]

    def __str__(self):
        return f"{self.schema_name}.{self.table_name}"


class FieldAsset(models.Model):
    class Origin(models.TextChoices):
        SOURCE = "SOURCE", "Source"
        PLATFORM = "PLATFORM", "Platform"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_asset = models.ForeignKey(TableAsset, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=180)
    logical_type = models.CharField(max_length=40)
    native_type = models.CharField(max_length=120)
    ordinal_position = models.PositiveIntegerField()
    nullable = models.BooleanField(default=True)
    default_value = models.TextField(blank=True)
    max_length = models.IntegerField(null=True, blank=True)
    numeric_precision = models.IntegerField(null=True, blank=True)
    numeric_scale = models.IntegerField(null=True, blank=True)
    is_primary_key = models.BooleanField(default=False)
    is_identity = models.BooleanField(default=False)
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.SOURCE)

    business_name = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["ordinal_position"]
        constraints = [models.UniqueConstraint(fields=["table_asset", "name"], name="unique_field_per_catalog_table")]

    def __str__(self):
        return f"{self.table_asset}.{self.name}"


class FieldContentRule(models.Model):
    class Mode(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        DAX = "DAX", "DAX"
        SQL = "SQL", "SQL"
        PYTHON = "PYTHON", "Python"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field = models.OneToOneField(FieldAsset, on_delete=models.CASCADE, related_name="content_rule")
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.MANUAL)
    expression = models.TextField(blank=True)
    dependencies = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="field_content_rules_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["field__table_asset__table_name", "field__ordinal_position"]

    def __str__(self):
        return f"{self.field} / {self.mode}"


class RelationAsset(models.Model):
    class Cardinality(models.TextChoices):
        ONE_TO_ONE = "ONE_TO_ONE", "One to one"
        ONE_TO_MANY = "ONE_TO_MANY", "One to many"
        MANY_TO_ONE = "MANY_TO_ONE", "Many to one"
        MANY_TO_MANY = "MANY_TO_MANY", "Many to many"

    class CrossFilterDirection(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        BOTH = "BOTH", "Both"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="relation_assets")
    name = models.CharField(max_length=240)
    source_table = models.ForeignKey(TableAsset, on_delete=models.CASCADE, related_name="outgoing_relations")
    target_table = models.ForeignKey(TableAsset, on_delete=models.CASCADE, related_name="incoming_relations")
    source_columns = models.JSONField(default=list)
    target_columns = models.JSONField(default=list)
    cardinality = models.CharField(max_length=20, choices=Cardinality.choices, default=Cardinality.ONE_TO_MANY)
    cross_filter_direction = models.CharField(max_length=12, choices=CrossFilterDirection.choices, default=CrossFilterDirection.SINGLE)
    is_active = models.BooleanField(default=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["data_source", "name", "source_table"], name="unique_relation_per_source_name_table")]

    def __str__(self):
        return self.name
