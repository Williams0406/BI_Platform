from rest_framework import serializers

from datasources.models import DataSource
from workspaces.models import Membership

from .models import (
    GatewayDataSourceBinding,
    GatewayHeartbeat,
    GatewayJob,
    GatewayRegistration,
)


ADMIN_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def can_manage(user, workspace):
    return Membership.objects.filter(
        organization=workspace.organization,
        user=user,
        is_active=True,
        role__in=ADMIN_ROLES,
    ).exists()


class GatewayRegistrationSerializer(serializers.ModelSerializer):
    effective_status = serializers.SerializerMethodField()

    class Meta:
        model = GatewayRegistration
        fields = [
            "id",
            "workspace",
            "name",
            "status",
            "effective_status",
            "token_version",
            "agent_version",
            "platform",
            "hostname",
            "last_seen_at",
            "capabilities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "effective_status",
            "token_version",
            "agent_version",
            "platform",
            "hostname",
            "last_seen_at",
            "capabilities",
            "created_at",
            "updated_at",
        ]

    def get_effective_status(self, obj):
        from .services import refresh_online_status
        return refresh_online_status(obj)


class GatewayCreateSerializer(serializers.Serializer):
    workspace = serializers.UUIDField()
    name = serializers.CharField(max_length=180)


class GatewayEnrollSerializer(serializers.Serializer):
    gateway_id = serializers.UUIDField()
    enrollment_code = serializers.CharField()
    agent_version = serializers.CharField(required=False, allow_blank=True)
    platform = serializers.CharField(required=False, allow_blank=True)
    hostname = serializers.CharField(required=False, allow_blank=True)
    capabilities = serializers.DictField(required=False)


class GatewayHeartbeatSerializer(serializers.Serializer):
    agent_version = serializers.CharField(required=False, allow_blank=True)
    platform = serializers.CharField(required=False, allow_blank=True)
    hostname = serializers.CharField(required=False, allow_blank=True)
    capabilities = serializers.DictField(required=False)
    metrics = serializers.DictField(required=False)


class GatewayBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayDataSourceBinding
        fields = [
            "id",
            "gateway",
            "data_source",
            "local_connection_name",
            "enabled",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        gateway = attrs["gateway"]
        source = attrs["data_source"]
        if gateway.workspace_id != source.workspace_id:
            raise serializers.ValidationError(
                "Gateway y DataSource pertenecen a workspaces diferentes."
            )
        if source.mode != DataSource.Mode.PRIVATE_GATEWAY:
            raise serializers.ValidationError(
                "El DataSource debe tener mode PRIVATE_GATEWAY."
            )
        return attrs


class GatewayJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayJob
        fields = [
            "id",
            "gateway",
            "data_source",
            "operation",
            "payload",
            "status",
            "requested_by",
            "claimed_at",
            "lease_expires_at",
            "finished_at",
            "result",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class GatewayJobCreateSerializer(serializers.Serializer):
    operation = serializers.ChoiceField(choices=GatewayJob.Operation.choices)
    payload = serializers.DictField(required=False)

    def validate(self, attrs):
        operation = attrs["operation"]
        payload = attrs.get("payload") or {}

        if operation == GatewayJob.Operation.READ_PAGE:
            for key in ("schema", "table"):
                if not payload.get(key):
                    raise serializers.ValidationError(
                        f"READ_PAGE requiere '{key}'."
                    )
            limit = int(payload.get("limit", 100))
            if limit < 1 or limit > 1000:
                raise serializers.ValidationError(
                    "READ_PAGE limit debe estar entre 1 y 1000."
                )

        if operation in {
            GatewayJob.Operation.INSERT,
            GatewayJob.Operation.UPDATE,
            GatewayJob.Operation.DELETE,
        }:
            for key in ("schema", "table"):
                if not payload.get(key):
                    raise serializers.ValidationError(
                        f"{operation} requiere '{key}'."
                    )

        if operation == GatewayJob.Operation.INSERT:
            if not isinstance(payload.get("values"), dict) or not payload["values"]:
                raise serializers.ValidationError(
                    "INSERT requiere values no vacío."
                )

        if operation == GatewayJob.Operation.UPDATE:
            if not isinstance(payload.get("values"), dict) or not payload["values"]:
                raise serializers.ValidationError(
                    "UPDATE requiere values no vacío."
                )
            if not isinstance(payload.get("where"), dict) or not payload["where"]:
                raise serializers.ValidationError(
                    "UPDATE requiere where no vacío."
                )

        if operation == GatewayJob.Operation.DELETE:
            if not isinstance(payload.get("where"), dict) or not payload["where"]:
                raise serializers.ValidationError(
                    "DELETE requiere where no vacío."
                )

        return attrs


class AgentJobResultSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    result = serializers.DictField(required=False)
    error_message = serializers.CharField(required=False, allow_blank=True)

from .models import GatewayImportRequest
class GatewayImportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model=GatewayImportRequest
        fields=["id","workspace","data_source","scope","selected_tables","status","progress","table_progress","catalog_job","requested_by","error_message","created_at","updated_at"]
        read_only_fields=["id","workspace","status","progress","table_progress","catalog_job","requested_by","error_message","created_at","updated_at"]
    def validate_selected_tables(self,value):
        if not isinstance(value,list): raise serializers.ValidationError("selected_tables debe ser una lista.")
        return value
