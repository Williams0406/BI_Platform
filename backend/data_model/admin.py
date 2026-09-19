from django.contrib import admin

from .models import FieldAsset, RelationAsset, TableAsset


class FieldInline(admin.TabularInline):
    model = FieldAsset
    extra = 0
    readonly_fields = [
        "name",
        "logical_type",
        "native_type",
        "ordinal_position",
        "nullable",
        "is_primary_key",
        "is_identity",
    ]


@admin.register(TableAsset)
class TableAssetAdmin(admin.ModelAdmin):
    list_display = [
        "schema_name",
        "table_name",
        "object_type",
        "data_source",
        "last_synced_at",
    ]
    list_filter = ["object_type", "data_source"]
    search_fields = ["schema_name", "table_name"]
    inlines = [FieldInline]


@admin.register(RelationAsset)
class RelationAssetAdmin(admin.ModelAdmin):
    list_display = ["name", "source_table", "target_table", "data_source"]
    search_fields = ["name"]
