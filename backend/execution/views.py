from celery import current_app
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Execution
from .serializers import ExecutionSerializer, ExecutionEventSerializer
from .services import request_cancel


class ExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Execution.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .prefetch_related("logs")
            .distinct()
        )

        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)

        exec_status = self.request.query_params.get("status")
        if exec_status:
            queryset = queryset.filter(status=exec_status)

        object_type = self.request.query_params.get("object_type")
        if object_type:
            queryset = queryset.filter(object_type=object_type)

        return queryset

    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        execution = self.get_object()
        after = request.query_params.get("after")
        qs = execution.events.all()
        if after:
            try:
                qs = qs.filter(sequence__gt=int(after))
            except (TypeError, ValueError):
                pass
        return Response(ExecutionEventSerializer(qs[:1000], many=True).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        execution = self.get_object()

        if execution.celery_task_id:
            current_app.control.revoke(
                execution.celery_task_id,
                terminate=False,
            )

        changed = request_cancel(execution)
        return Response(
            {
                "cancelled": changed,
                "status": execution.status,
            }
        )
