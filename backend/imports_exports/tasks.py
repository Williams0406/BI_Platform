from celery import shared_task
from django.utils import timezone
from execution.models import Execution
from execution.services import create_execution, mark_failed, ExecutionCancelled

from .models import ExportJob, ImportJob, SourceSyncPolicy
from .services import execute_export, execute_import, execute_source_sync


@shared_task(bind=True, name="imports_exports.tasks.run_import_task")
def run_import_task(self, execution_id, job_id):
    execution = Execution.objects.get(id=execution_id)
    job = ImportJob.objects.select_related("workspace", "target_table", "target_table__data_source", "target_table__data_asset", "created_by").get(id=job_id)
    execution.celery_task_id = self.request.id or ""
    execution.save(update_fields=["celery_task_id"])
    try:
        return execute_import(job, execution)
    except ExecutionCancelled:
        job.status = ImportJob.Status.CANCELLED if hasattr(ImportJob.Status,"CANCELLED") else ImportJob.Status.FAILED
        job.finished_at = timezone.now(); job.save(update_fields=["status","finished_at"]); return {"cancelled":True}
    except Exception as exc:
        job.status = ImportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error_report = (job.error_report or []) + [{"error": str(exc)}]
        job.save(update_fields=["status", "finished_at", "error_report"])
        mark_failed(execution, exc)
        raise


@shared_task(bind=True, name="imports_exports.tasks.run_export_task")
def run_export_task(self, execution_id, job_id):
    execution = Execution.objects.get(id=execution_id)
    job = ExportJob.objects.select_related("workspace", "source_table", "source_table__data_source", "created_by").get(id=job_id)
    execution.celery_task_id = self.request.id or ""
    execution.save(update_fields=["celery_task_id"])
    try:
        return execute_export(job, execution)
    except ExecutionCancelled:
        if hasattr(ExportJob.Status,"CANCELLED"): job.status=ExportJob.Status.CANCELLED; job.finished_at=timezone.now(); job.save(update_fields=["status","finished_at"])
        return {"cancelled":True}
    except Exception as exc:
        job.status = ExportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error_message = str(exc)
        job.save(update_fields=["status", "finished_at", "error_message"])
        mark_failed(execution, exc)
        raise


@shared_task(bind=True, name="imports_exports.tasks.run_source_sync_task")
def run_source_sync_task(self, execution_id, policy_id):
    execution = Execution.objects.get(id=execution_id)
    policy = SourceSyncPolicy.objects.select_related(
        "workspace", "source_data_source", "source_table", "target_table", "created_by"
    ).prefetch_related("source_table__fields", "target_table__fields").get(id=policy_id)
    execution.celery_task_id = self.request.id or ""
    execution.save(update_fields=["celery_task_id"])
    try:
        return execute_source_sync(policy, execution)
    except ExecutionCancelled:
        policy.status = SourceSyncPolicy.Status.FAILED; policy.last_error="Cancelled by user."; policy.save(update_fields=["status","last_error","updated_at"]); return {"cancelled":True}
    except Exception as exc:
        policy.status = SourceSyncPolicy.Status.FAILED
        policy.last_error = str(exc)
        policy.save(update_fields=["status", "last_error", "updated_at"])
        mark_failed(execution, exc)
        raise


def queue_policy_execution(policy, requested_by=None):
    execution = create_execution(
        workspace=policy.workspace,
        object_type=Execution.ObjectType.IMPORT,
        object_id=policy.id,
        queue="imports",
        requested_by=requested_by or policy.created_by,
    )
    policy.status = SourceSyncPolicy.Status.QUEUED
    policy.execution_id = execution.id
    policy.save(update_fields=["status", "execution_id", "updated_at"])
    result = run_source_sync_task.apply_async(args=[str(execution.id), str(policy.id)], queue="imports")
    execution.celery_task_id = result.id or ""
    execution.save(update_fields=["celery_task_id"])
    return execution


@shared_task(name="imports_exports.tasks.dispatch_due_source_syncs")
def dispatch_due_source_syncs():
    now = timezone.now()
    due = SourceSyncPolicy.objects.filter(
        enabled=True,
        next_run_at__isnull=False,
        next_run_at__lte=now,
    ).exclude(status__in=[SourceSyncPolicy.Status.QUEUED, SourceSyncPolicy.Status.RUNNING])[:50]
    queued = 0
    for policy in due:
        queue_policy_execution(policy)
        queued += 1
    return {"queued": queued}
