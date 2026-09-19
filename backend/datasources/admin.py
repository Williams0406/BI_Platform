from django.contrib import admin

from .models import DataAsset, DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "workspace",
        "mode",
        "engine",
        "status",
        "can_read",
        "can_write",
        "can_ddl",
    ]
    list_filter = ["mode", "engine", "status"]
    search_fields = ["name", "workspace__name"]


@admin.register(DataAsset)
class DataAssetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "workspace",
        "asset_type",
        "status",
        "version",
    ]
    list_filter = ["asset_type", "status"]
    search_fields = ["name", "workspace__name", "physical_name"]
