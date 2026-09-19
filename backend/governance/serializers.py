from rest_framework import serializers
from workspaces.models import Membership
from .models import AuditLog, DestructiveChangeRequest, ResourcePermission, RetentionPolicy, WorkspaceQuota, WorkspaceUsage, WorkspacePolicy

class AuditLogSerializer(serializers.ModelSerializer):
    actor_email=serializers.EmailField(source="actor.email",read_only=True)
    class Meta:
        model=AuditLog
        fields=["id","workspace","actor","actor_email","action","resource_type","resource_id","detail","ip_address","created_at"]

class WorkspaceQuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model=WorkspaceQuota
        fields="__all__"

class WorkspaceUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model=WorkspaceUsage
        fields="__all__"

class ResourcePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model=ResourcePermission
        fields="__all__"
        read_only_fields=["id","created_at"]

class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model=RetentionPolicy
        fields="__all__"

class DestructiveChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model=DestructiveChangeRequest
        fields="__all__"
        read_only_fields=["id","status","requested_by","approved_by","created_at","approved_at","executed_at"]

class DataSourceSecretWriteSerializer(serializers.Serializer):
    credentials=serializers.DictField(write_only=True)

class SecretStatusSerializer(serializers.Serializer):
    configured=serializers.BooleanField()
    key_version=serializers.IntegerField(required=False)
    updated_at=serializers.DateTimeField(required=False)

class WorkspacePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model=WorkspacePolicy
        fields="__all__"


from .models import DataCopyEvent
class DataCopyEventSerializer(serializers.ModelSerializer):
    actor_email=serializers.EmailField(source="actor.email",read_only=True)
    class Meta:
        model=DataCopyEvent
        fields=["id","workspace","source","binding","kind","title","summary","detail","version","published","actor","actor_email","created_at"]
        read_only_fields=["id","actor","created_at"]
