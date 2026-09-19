from django.contrib import admin

from .models import Membership, Organization, Workspace


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["status"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["organization", "user", "role", "is_active", "joined_at"]
    list_filter = ["role", "is_active"]
    search_fields = ["organization__name", "user__email"]


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "status", "created_at"]
    search_fields = ["name", "slug", "organization__name"]
    list_filter = ["status"]
