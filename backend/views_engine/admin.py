from django.contrib import admin

from .models import ViewActionRule, ViewDefinition, ViewFieldBinding


class BindingInline(admin.TabularInline):
    model = ViewFieldBinding
    extra = 0


class ActionRuleInline(admin.TabularInline):
    model = ViewActionRule
    extra = 0


@admin.register(ViewDefinition)
class ViewDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "view_type", "workspace", "source_table", "status"]
    list_filter = ["view_type", "status"]
    search_fields = ["name", "workspace__name", "source_table__table_name"]
    inlines = [BindingInline, ActionRuleInline]
