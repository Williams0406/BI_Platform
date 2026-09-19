from django.contrib import admin

from .models import AssetDependency, AssetState, ChangeEvent


@admin.register(AssetDependency)
class AssetDependencyAdmin(admin.ModelAdmin):
    list_display = ["upstream", "downstream", "refresh_policy", "active"]
    list_filter = ["dependency_type", "refresh_policy", "active"]


@admin.register(AssetState)
class AssetStateAdmin(admin.ModelAdmin):
    list_display = ["asset", "status", "version", "last_changed_at"]
    list_filter = ["status"]


@admin.register(ChangeEvent)
class ChangeEventAdmin(admin.ModelAdmin):
    list_display = ["asset", "change_type", "record_key", "created_at", "propagated_at"]
    list_filter = ["change_type"]
