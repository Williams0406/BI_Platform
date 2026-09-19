from rest_framework import serializers

from .models import Execution, ExecutionLog, ExecutionEvent


class ExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionLog
        fields = ["id", "level", "message", "metadata", "created_at"]


class ExecutionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionEvent
        fields = ["id", "sequence", "family", "event_type", "payload", "created_at"]


class ExecutionSerializer(serializers.ModelSerializer):
    logs = ExecutionLogSerializer(many=True, read_only=True)

    class Meta:
        model = Execution
        fields = [
            "id",
            "workspace",
            "object_type",
            "object_id",
            "queue",
            "status",
            "progress",
            "celery_task_id",
            "parameters",
            "result",
            "error_type",
            "error_message",
            "queued_at",
            "started_at",
            "finished_at",
            "duration_ms",
            "logs",
        ]
