import time

from django.db import transaction
from django.utils import timezone

from .models import Execution, ExecutionLog


def create_execution(
    *,
    workspace,
    object_type,
    object_id=None,
    queue="fast",
    requested_by=None,
    parameters=None,
):
    return Execution.objects.create(
        workspace=workspace,
        object_type=object_type,
        object_id=object_id,
        queue=queue,
        requested_by=requested_by,
        parameters=parameters or {},
    )


def append_log(execution, message, level=ExecutionLog.Level.INFO, metadata=None):
    return ExecutionLog.objects.create(
        execution=execution,
        level=level,
        message=message,
        metadata=metadata or {},
    )


def mark_running(execution):
    execution.status = Execution.Status.RUNNING
    execution.started_at = timezone.now()
    execution.progress = max(execution.progress, 1)
    execution.save(update_fields=["status", "started_at", "progress"])
    append_log(execution, "Ejecución iniciada.")
    emit_event(execution, "EXECUTION_STARTED", {"progress": execution.progress}, family="EXECUTION")


def mark_success(execution, result=None):
    finished = timezone.now()
    execution.status = Execution.Status.SUCCESS
    execution.progress = 100
    execution.finished_at = finished
    execution.result = result or {}
    if execution.started_at:
        execution.duration_ms = int(
            (finished - execution.started_at).total_seconds() * 1000
        )
    execution.save(
        update_fields=[
            "status",
            "progress",
            "finished_at",
            "result",
            "duration_ms",
        ]
    )
    append_log(execution, "Ejecución completada correctamente.")
    emit_event(execution, "EXECUTION_COMPLETED", {"progress": 100, "result": execution.result}, family="EXECUTION")


def mark_failed(execution, exc):
    finished = timezone.now()
    execution.status = Execution.Status.FAILED
    execution.finished_at = finished
    execution.error_type = exc.__class__.__name__
    execution.error_message = str(exc)
    if execution.started_at:
        execution.duration_ms = int(
            (finished - execution.started_at).total_seconds() * 1000
        )
    execution.save(
        update_fields=[
            "status",
            "finished_at",
            "error_type",
            "error_message",
            "duration_ms",
        ]
    )
    append_log(
        execution,
        f"Falló la ejecución: {exc}",
        level=ExecutionLog.Level.ERROR,
    )
    emit_event(execution, "EXECUTION_FAILED", {"error_type": execution.error_type, "error_message": execution.error_message}, family="EXECUTION")


def update_progress(execution, progress, message=None):
    progress = max(0, min(int(progress), 100))
    execution.progress = progress
    execution.save(update_fields=["progress"])
    if message:
        append_log(execution, message)
    emit_event(execution, "EXECUTION_PROGRESS", {"progress": progress, "message": message or ""}, family="EXECUTION")


def request_cancel(execution):
    if execution.status not in {
        Execution.Status.QUEUED,
        Execution.Status.RUNNING,
    }:
        return False

    execution.status = Execution.Status.CANCELLED
    execution.finished_at = timezone.now()
    execution.save(update_fields=["status", "finished_at"])
    append_log(execution, "Cancelación solicitada.")
    return True



class ExecutionCancelled(RuntimeError):
    """Raised cooperatively when an execution has been cancelled."""


def ensure_not_cancelled(execution):
    """Refresh status and stop a long-running service at safe checkpoints."""
    execution.refresh_from_db(fields=["status"])
    if execution.status == Execution.Status.CANCELLED:
        raise ExecutionCancelled("Execution cancelled by user.")
    return execution


def emit_event(execution, event_type, payload=None, family="EXECUTION"):
    """Persist one normalized UER event with a monotonic sequence per execution."""
    from .models import ExecutionEvent
    with transaction.atomic():
        locked = Execution.objects.select_for_update().get(pk=execution.pk)
        last = locked.events.order_by("-sequence").values_list("sequence", flat=True).first() or 0
        return ExecutionEvent.objects.create(
            execution=locked,
            sequence=last + 1,
            family=family,
            event_type=event_type,
            payload=payload or {},
        )


def report_metric(execution, name, value, step=None, scope="run"):
    payload = {"name": name, "value": value, "scope": scope}
    if step is not None:
        payload["step"] = step
    return emit_event(execution, "METRIC_REPORTED", payload, family="METRIC")
