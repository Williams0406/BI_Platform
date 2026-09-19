from django.contrib import admin

from .models import SQLTransformation, TransformationInput


class TransformationInputInline(admin.TabularInline):
    model = TransformationInput
    extra = 0


@admin.register(SQLTransformation)
class SQLTransformationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "workspace",
        "output_mode",
        "refresh_policy",
        "enabled",
        "updated_at",
    ]
    list_filter = ["output_mode", "refresh_policy", "enabled"]
    search_fields = ["name"]
    inlines = [TransformationInputInline]
