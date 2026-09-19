from rest_framework import serializers
from django.utils import timezone

from data_model.models import TableAsset
from datasources.models import DataSource
from governance.services import get_quota
from workspaces.models import Membership

from .models import ExportJob, ImportJob, SourceSyncPolicy

WRITE_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.BUILDER}


def can_write(user, workspace):
    return Membership.objects.filter(
        organization=workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = [
            "id", "workspace", "target_table", "target_table_name", "target_display_name",
            "file", "file_type", "sheet_name", "mode", "column_mapping", "inferred_schema",
            "status", "execution_id", "rows_total", "rows_valid", "rows_imported", "rows_failed",
            "error_report", "created_at", "finished_at",
        ]
        read_only_fields = [
            "id", "inferred_schema", "status", "execution_id", "rows_total", "rows_valid",
            "rows_imported", "rows_failed", "error_report", "created_at", "finished_at",
        ]

    def validate(self, attrs):
        ws = attrs["workspace"]
        table = attrs.get("target_table")
        mode = attrs.get("mode", ImportJob.Mode.CREATE)
        if not can_write(self.context["request"].user, ws):
            raise serializers.ValidationError("Sin permisos de importación.")
        if mode == ImportJob.Mode.CREATE:
            if table:
                raise serializers.ValidationError({"target_table": "CREATE no requiere tabla destino."})
            if not attrs.get("target_table_name"):
                raise serializers.ValidationError({"target_table_name": "Indique el nombre de la nueva tabla."})
        else:
            if not table:
                raise serializers.ValidationError({"target_table": "Seleccione una tabla MANAGED destino."})
            if table.data_source.workspace_id != ws.id:
                raise serializers.ValidationError("Tabla y workspace no coinciden.")
            if table.data_source.mode != DataSource.Mode.MANAGED:
                raise serializers.ValidationError("APPEND, REPLACE y UPSERT requieren una tabla MANAGED.")
        return attrs

    def create(self, validated_data):
        return ImportJob.objects.create(created_by=self.context["request"].user, **validated_data)


class SourceSyncPolicySerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source_data_source.name", read_only=True)
    source_table_label = serializers.SerializerMethodField()
    target_table_label = serializers.SerializerMethodField()

    class Meta:
        model = SourceSyncPolicy
        fields = [
            "id", "workspace", "source_data_source", "source_name", "source_table",
            "source_table_label", "target_table", "target_table_label", "target_table_name",
            "target_display_name", "strategy", "schedule", "custom_interval_minutes",
            "incremental_field", "last_cursor_value", "enabled", "status", "last_sync_at",
            "next_run_at", "last_rows", "last_error", "execution_id", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "target_table", "last_cursor_value", "status", "last_sync_at", "next_run_at",
            "last_rows", "last_error", "execution_id", "created_at", "updated_at",
        ]

    def get_source_table_label(self, obj):
        return obj.source_table.technical_name or obj.source_table.table_name

    def get_target_table_label(self, obj):
        if not obj.target_table:
            return None
        return obj.target_table.technical_name or obj.target_table.table_name

    def validate(self, attrs):
        instance = self.instance
        ws = attrs.get("workspace", getattr(instance, "workspace", None))
        source = attrs.get("source_data_source", getattr(instance, "source_data_source", None))
        source_table = attrs.get("source_table", getattr(instance, "source_table", None))
        strategy = attrs.get("strategy", getattr(instance, "strategy", SourceSyncPolicy.Strategy.FULL))
        incremental_field = attrs.get("incremental_field", getattr(instance, "incremental_field", ""))
        schedule = attrs.get("schedule", getattr(instance, "schedule", SourceSyncPolicy.Schedule.MANUAL))
        interval = attrs.get("custom_interval_minutes", getattr(instance, "custom_interval_minutes", 60))

        if not ws or not can_write(self.context["request"].user, ws):
            raise serializers.ValidationError("Sin permisos para configurar sincronización.")
        if not source or source.workspace_id != ws.id:
            raise serializers.ValidationError({"source_data_source": "La fuente debe pertenecer al workspace."})
        if source.mode not in {DataSource.Mode.EXTERNAL, DataSource.Mode.PRIVATE_GATEWAY}:
            raise serializers.ValidationError({"source_data_source": "Solo EXTERNAL o PRIVATE_GATEWAY pueden sincronizarse a Managed."})
        if not source.can_read:
            raise serializers.ValidationError({"source_data_source": "La fuente requiere capacidad READ."})
        if not source_table or source_table.data_source_id != source.id:
            raise serializers.ValidationError({"source_table": "La tabla no pertenece a la fuente seleccionada."})
        if strategy == SourceSyncPolicy.Strategy.INCREMENTAL:
            names = set(source_table.fields.values_list("name", flat=True))
            if not incremental_field or incremental_field not in names:
                raise serializers.ValidationError({"incremental_field": "Seleccione un campo válido para el cursor incremental."})
        if schedule == SourceSyncPolicy.Schedule.CUSTOM and int(interval or 0) < 5:
            raise serializers.ValidationError({"custom_interval_minutes": "El intervalo personalizado mínimo es 5 minutos."})
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class ExportJobSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportJob
        fields = [
            "id", "workspace", "source_table", "file_type", "columns", "filters", "row_limit",
            "output_file", "download_url", "status", "execution_id", "rows_exported", "created_at",
            "finished_at", "error_message",
        ]
        read_only_fields = [
            "id", "output_file", "download_url", "status", "execution_id", "rows_exported",
            "created_at", "finished_at", "error_message",
        ]

    def get_download_url(self, obj):
        return obj.output_file.url if obj.output_file else None

    def validate(self, attrs):
        ws = attrs["workspace"]
        table = attrs["source_table"]
        if table.data_source.workspace_id != ws.id:
            raise serializers.ValidationError("Tabla y workspace no coinciden.")
        if not can_write(self.context["request"].user, ws):
            raise serializers.ValidationError("Sin permisos de exportación.")
        quota = get_quota(ws)
        if attrs.get("row_limit", 100000) > quota.max_export_rows:
            raise serializers.ValidationError("row_limit supera la cuota.")
        return attrs

    def create(self, validated_data):
        return ExportJob.objects.create(created_by=self.context["request"].user, **validated_data)
