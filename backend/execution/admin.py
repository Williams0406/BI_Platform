from django.contrib import admin

from .models import Execution, ExecutionLog


class ExecutionLogInline(admin.TabularInline):
    model = ExecutionLog
    extra = 0
    readonly_fields = ["level", "message", "metadata", "created_at"]


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = [
        "object_type",
        "object_id",
        "workspace",
        "queue",
        "status",
        "progress",
        "queued_at",
        "duration_ms",
    ]
    list_filter = ["object_type", "queue", "status"]
    search_fields = ["object_id", "celery_task_id"]
    inlines = [ExecutionLogInline]
