from django.db import connection
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from execution.models import Execution
from execution.services import create_execution
from workspaces.models import Membership

from .models import SQLTransformation
from .serializers import SQLTransformationSerializer, TransformationPreviewSerializer
from .sql_validation import SQLValidationError, resolve_asset_tokens, validate_select_sql
from .tasks import run_sql_transformation_task


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def can_write(user, transformation):
    return Membership.objects.filter(
        organization=transformation.workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()


class SQLTransformationViewSet(viewsets.ModelViewSet):
    serializer_class = SQLTransformationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            SQLTransformation.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace", "workspace__organization", "output_asset")
            .prefetch_related("inputs__asset")
            .distinct()
        )

        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        return queryset

    def perform_update(self, serializer):
        obj = self.get_object()
        if not can_write(self.request.user, obj):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tiene permisos de edición.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_write(self.request.user, instance):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tiene permisos de eliminación.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        transformation = self.get_object()
        serializer = TransformationPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        limit = serializer.validated_data["limit"]

        try:
            sql_text = validate_select_sql(transformation.sql)
            rendered, used_assets = resolve_asset_tokens(
                sql_text,
                transformation.workspace,
            )

            # Wrap validated SELECT, limiting preview size.
            query = f"SELECT * FROM ({rendered}) AS preview_query LIMIT %s"
            with connection.cursor() as cursor:
                cursor.execute(query, [limit])
                names = [col[0] for col in cursor.description]
                rows = [dict(zip(names, row)) for row in cursor.fetchall()]

            return Response(
                {
                    "columns": names,
                    "rows": rows,
                    "returned": len(rows),
                    "input_assets": [str(asset.id) for asset in used_assets],
                }
            )
        except SQLValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        transformation = self.get_object()
        if not can_write(request.user, transformation):
            return Response(status=status.HTTP_403_FORBIDDEN)

        execution = create_execution(
            workspace=transformation.workspace,
            object_type=Execution.ObjectType.SQL_TRANSFORMATION,
            object_id=transformation.id,
            queue="sql",
            requested_by=request.user,
        )

        async_result = run_sql_transformation_task.apply_async(
            args=[str(execution.id)],
            queue="sql",
        )
        execution.celery_task_id = async_result.id or ""
        execution.save(update_fields=["celery_task_id"])

        return Response(
            {
                "execution_id": str(execution.id),
                "celery_task_id": execution.celery_task_id,
                "status": execution.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )
