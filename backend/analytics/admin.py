from django.contrib import admin

from .models import ChartDefinition, DashboardDefinition, DashboardItem, ReportDefinition


class DashboardItemInline(admin.TabularInline):
    model = DashboardItem
    extra = 0


@admin.register(ChartDefinition)
class ChartDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "chart_type", "workspace", "metric", "updated_at"]
    list_filter = ["chart_type"]
    search_fields = ["name"]


@admin.register(DashboardDefinition)
class DashboardDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "updated_at"]
    search_fields = ["name"]
    inlines = [DashboardItemInline]


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "dashboard", "default_export_format"]
    list_filter = ["default_export_format"]
    search_fields = ["name"]
