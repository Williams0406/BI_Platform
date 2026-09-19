from django.contrib import admin

from .models import (
    GatewayDataSourceBinding,
    GatewayHeartbeat,
    GatewayJob,
    GatewayRegistration,
)


class BindingInline(admin.TabularInline):
    model = GatewayDataSourceBinding
    extra = 0


@admin.register(GatewayRegistration)
class GatewayRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "workspace",
        "status",
        "hostname",
        "agent_version",
        "token_version",
        "last_seen_at",
    ]
    list_filter = ["status"]
    search_fields = ["name", "hostname", "workspace__name"]
    readonly_fields = [
        "agent_token_hash",
        "enrollment_code_hash",
        "last_seen_at",
        "last_ip",
        "created_at",
        "updated_at",
    ]
    inlines = [BindingInline]


@admin.register(GatewayJob)
class GatewayJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "gateway",
        "data_source",
        "operation",
        "status",
        "created_at",
        "finished_at",
    ]
    list_filter = ["operation", "status"]
    search_fields = ["id", "data_source__name"]


@admin.register(GatewayHeartbeat)
class GatewayHeartbeatAdmin(admin.ModelAdmin):
    list_display = ["gateway", "agent_version", "created_at"]
