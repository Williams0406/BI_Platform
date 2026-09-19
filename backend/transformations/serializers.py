from rest_framework import serializers

from workspaces.models import Membership

from .models import SQLTransformation, TransformationInput
from .sql_validation import validate_select_sql


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


class TransformationInputSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = TransformationInput
        fields = ["id", "asset", "asset_name", "alias"]


class SQLTransformationSerializer(serializers.ModelSerializer):
    inputs = TransformationInputSerializer(many=True, read_only=True)

    class Meta:
        model = SQLTransformation
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "sql",
            "output_mode",
            "output_asset",
            "refresh_policy",
            "enabled",
            "inputs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "output_asset", "created_at", "updated_at"]

    def validate_workspace(self, workspace):
        request = self.context["request"]
        allowed = Membership.objects.filter(
            organization=workspace.organization,
            user=request.user,
            is_active=True,
            role__in=WRITE_ROLES,
        ).exists()
        if not allowed:
            raise serializers.ValidationError(
                "No tiene permisos para crear transformaciones en este workspace."
            )
        return workspace

    def validate_sql(self, value):
        validate_select_sql(value)
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class TransformationPreviewSerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=100, min_value=1, max_value=500)
