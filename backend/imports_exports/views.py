from django.http import FileResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from execution.models import Execution
from execution.services import create_execution
from governance.services import QuotaExceeded, assert_can_start_job, audit

from .models import ExportJob, ImportJob, SourceSyncPolicy
from .serializers import ExportJobSerializer, ImportJobSerializer, SourceSyncPolicySerializer
from .services import initialize_policy_schedule, preview_import, inspect_uploaded_file
from .tasks import queue_policy_execution, run_export_task, run_import_task


class ImportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ImportJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ImportJob.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related("workspace", "target_table").distinct()
        ws = self.request.query_params.get("workspace")
        return qs.filter(workspace_id=ws) if ws else qs

    @action(detail=False, methods=["post"], url_path="inspect")
    def inspect_file(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Seleccione un archivo."}, status=400)
        try:
            return Response(inspect_uploaded_file(upload, request.data.get("sheet_name", "")))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        job = self.get_object()
        return Response(preview_import(job))

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        job = self.get_object()
        if job.status not in {ImportJob.Status.UPLOADED, ImportJob.Status.FAILED}:
            return Response({"detail": "Job no ejecutable."}, status=409)
        try:
            assert_can_start_job(job.workspace)
        except QuotaExceeded as exc:
            return Response({"detail": str(exc)}, status=429)
        execution = create_execution(
            workspace=job.workspace,
            object_type=Execution.ObjectType.IMPORT,
            object_id=job.id,
            queue="imports",
            requested_by=request.user,
        )
        job.status = ImportJob.Status.QUEUED
        job.execution_id = execution.id
        job.save(update_fields=["status", "execution_id"])
        result = run_import_task.apply_async(args=[str(execution.id), str(job.id)], queue="imports")
        execution.celery_task_id = result.id or ""
        execution.save(update_fields=["celery_task_id"])
        audit(job.workspace, "IMPORT_QUEUE", "ImportJob", job.id, request.user)
        return Response({"import_job_id": str(job.id), "execution_id": str(execution.id), "status": job.status}, status=202)


class SourceSyncPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = SourceSyncPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SourceSyncPolicy.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related(
            "workspace", "source_data_source", "source_table", "target_table"
        ).prefetch_related("source_table__fields").distinct()
        ws = self.request.query_params.get("workspace")
        source = self.request.query_params.get("source_data_source")
        if ws:
            qs = qs.filter(workspace_id=ws)
        if source:
            qs = qs.filter(source_data_source_id=source)
        return qs

    def perform_create(self, serializer):
        policy = serializer.save()
        initialize_policy_schedule(policy)
        audit(policy.workspace, "SOURCE_SYNC_POLICY_CREATE", "SourceSyncPolicy", policy.id, self.request.user)

    def perform_update(self, serializer):
        policy = serializer.save()
        initialize_policy_schedule(policy)
        audit(policy.workspace, "SOURCE_SYNC_POLICY_UPDATE", "SourceSyncPolicy", policy.id, self.request.user)

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        policy = self.get_object()
        if policy.status in {SourceSyncPolicy.Status.QUEUED, SourceSyncPolicy.Status.RUNNING}:
            return Response({"detail": "La sincronización ya está en ejecución."}, status=409)
        try:
            assert_can_start_job(policy.workspace)
        except QuotaExceeded as exc:
            return Response({"detail": str(exc)}, status=429)
        execution = queue_policy_execution(policy, requested_by=request.user)
        audit(policy.workspace, "SOURCE_SYNC_QUEUE", "SourceSyncPolicy", policy.id, request.user)
        return Response({"sync_policy_id": str(policy.id), "execution_id": str(execution.id), "status": policy.status}, status=202)


class ExportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ExportJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ExportJob.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related("workspace", "source_table").distinct()
        ws = self.request.query_params.get("workspace")
        return qs.filter(workspace_id=ws) if ws else qs

    def perform_create(self, serializer):
        job = serializer.save()
        try:
            assert_can_start_job(job.workspace)
        except QuotaExceeded as exc:
            job.delete()
            raise ValidationError({"detail": str(exc)})
        execution = create_execution(
            workspace=job.workspace,
            object_type=Execution.ObjectType.EXPORT,
            object_id=job.id,
            queue="imports",
            requested_by=self.request.user,
        )
        job.execution_id = execution.id
        job.save(update_fields=["execution_id"])
        result = run_export_task.apply_async(args=[str(execution.id), str(job.id)], queue="imports")
        execution.celery_task_id = result.id or ""
        execution.save(update_fields=["celery_task_id"])
        audit(job.workspace, "EXPORT_QUEUE", "ExportJob", job.id, self.request.user)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        job = self.get_object()
        if job.status != ExportJob.Status.SUCCESS or not job.output_file:
            return Response({"detail": "Export no disponible."}, status=409)
        return FileResponse(job.output_file.open("rb"), as_attachment=True, filename=job.output_file.name.split("/")[-1])
