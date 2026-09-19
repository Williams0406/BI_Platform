from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from .models import Membership, Organization, Workspace


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "user_email", "role", "is_active", "joined_at"]
        read_only_fields = ["id", "joined_at"]


class OrganizationSerializer(serializers.ModelSerializer):
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "current_user_role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "current_user_role"]

    def get_current_user_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        membership = obj.memberships.filter(
            user=request.user,
            is_active=True,
        ).first()
        return membership.role if membership else None

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        slug = validated_data.get("slug") or slugify(validated_data["name"])
        validated_data["slug"] = slug
        organization = Organization.objects.create(
            created_by=request.user,
            **validated_data,
        )
        Membership.objects.create(
            organization=organization,
            user=request.user,
            role=Membership.Role.OWNER,
        )
        return organization


class WorkspaceSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    class Meta:
        model = Workspace
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "slug",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_organization(self, organization):
        request = self.context["request"]
        allowed = Membership.objects.filter(
            organization=organization,
            user=request.user,
            is_active=True,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
                Membership.Role.BUILDER,
            ],
        ).exists()

        if not allowed:
            raise serializers.ValidationError(
                "No tiene permisos para crear workspaces en esta organización."
            )
        return organization

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)
