from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from execution.models import Execution, ExecutionLog
from governance.models import AuditLog, RetentionPolicy
from imports_exports.models import ExportJob, ImportJob


def _delete_filefield(field):
    try:
        if field:
            field.delete(save=False)
            return 1
    except Exception:
        pass
    return 0


def run_maintenance():
    now = timezone.now()
    result = {
        "stale_executions_failed": 0,
        "audit_logs_deleted": 0,
        "execution_logs_deleted": 0,
        "import_files_deleted": 0,
        "export_files_deleted": 0,
    }

    stale_cutoff = now - timedelta(minutes=settings.OPS_STALE_EXECUTION_MINUTES)
    stale = Execution.objects.filter(
        status=Execution.Status.RUNNING,
        started_at__lt=stale_cutoff,
    )
    result["stale_executions_failed"] = stale.update(
        status=Execution.Status.FAILED,
        finished_at=now,
        error_type="StaleExecution",
        error_message="Marked failed by production maintenance.",
    )

    for policy in RetentionPolicy.objects.select_related("workspace"):
        ws = policy.workspace

        audit_cutoff = now - timedelta(days=policy.audit_log_days)
        deleted, _ = AuditLog.objects.filter(
            workspace=ws, created_at__lt=audit_cutoff
        ).delete()
        result["audit_logs_deleted"] += deleted

        execution_cutoff = now - timedelta(days=policy.execution_log_days)
        deleted, _ = ExecutionLog.objects.filter(
            execution__workspace=ws,
            created_at__lt=execution_cutoff,
        ).delete()
        result["execution_logs_deleted"] += deleted

        import_cutoff = now - timedelta(days=policy.import_artifact_days)
        for job in ImportJob.objects.filter(
            workspace=ws, created_at__lt=import_cutoff
        ).exclude(file=""):
            result["import_files_deleted"] += _delete_filefield(job.file)
            job.file = ""
            job.save(update_fields=["file"])

        export_cutoff = now - timedelta(days=policy.export_artifact_days)
        for job in ExportJob.objects.filter(
            workspace=ws, created_at__lt=export_cutoff
        ).exclude(output_file=""):
            result["export_files_deleted"] += _delete_filefield(job.output_file)
            job.output_file = ""
            job.save(update_fields=["output_file"])

    return result
