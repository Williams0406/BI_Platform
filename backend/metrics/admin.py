from django.contrib import admin

from .models import MetricDefinition, SemanticDimension, SemanticModel


class SemanticDimensionInline(admin.TabularInline):
    model = SemanticDimension
    extra = 0


class MetricInline(admin.TabularInline):
    model = MetricDefinition
    extra = 0


@admin.register(SemanticModel)
class SemanticModelAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "base_table", "enabled", "updated_at"]
    search_fields = ["name", "workspace__name"]
    inlines = [SemanticDimensionInline, MetricInline]


@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "workspace",
        "semantic_model",
        "expression_type",
        "aggregation",
        "enabled",
    ]
    list_filter = ["expression_type", "aggregation", "enabled"]
    search_fields = ["name"]
