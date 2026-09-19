from rest_framework import serializers

from datasources.models import DataAsset
from workspaces.models import Workspace

from .models import AssetDependency, AssetState, ChangeEvent


class AssetStateSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = AssetState
        fields = [
            "asset",
            "asset_name",
            "status",
            "version",
            "last_changed_at",
            "last_success_at",
            "last_error",
        ]


class AssetDependencySerializer(serializers.ModelSerializer):
    upstream_name = serializers.CharField(source="upstream.name", read_only=True)
    downstream_name = serializers.CharField(source="downstream.name", read_only=True)

    class Meta:
        model = AssetDependency
        fields = [
            "id",
            "workspace",
            "upstream",
            "upstream_name",
            "downstream",
            "downstream_name",
            "dependency_type",
            "refresh_policy",
            "active",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DependencyCreateSerializer(serializers.Serializer):
    workspace = serializers.PrimaryKeyRelatedField(queryset=Workspace.objects.all())
    upstream = serializers.PrimaryKeyRelatedField(queryset=DataAsset.objects.all())
    downstream = serializers.PrimaryKeyRelatedField(queryset=DataAsset.objects.all())
    dependency_type = serializers.ChoiceField(
        choices=AssetDependency.DependencyType.choices,
        default=AssetDependency.DependencyType.DATA,
    )
    refresh_policy = serializers.ChoiceField(
        choices=AssetDependency.RefreshPolicy.choices,
        default=AssetDependency.RefreshPolicy.MARK_STALE,
    )
    metadata = serializers.JSONField(required=False)


class ChangeEventSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = ChangeEvent
        fields = [
            "id",
            "workspace",
            "asset",
            "asset_name",
            "change_type",
            "record_key",
            "metadata",
            "created_at",
            "propagated_at",
        ]
