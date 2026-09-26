from celery import shared_task

from execution.models import Execution
from execution.services import mark_failed, ExecutionCancelled

from .models import OptimizationRun
from .services import execute_optimization


@shared_task(bind=True, name="optimization.tasks.run_optimization_task")
def run_optimization_task(self, execution_id, optimization_run_id):
    execution = Execution.objects.get(id=execution_id)
    run = OptimizationRun.objects.select_related(
        "model",
        "model__workspace",
        "model__created_by",
        "scenario",
        "solver_config",
    ).get(id=optimization_run_id)

    if execution.status == Execution.Status.CANCELLED:
        run.status = OptimizationRun.Status.CANCELLED
        run.save(update_fields=["status"])
        return {"cancelled": True}

    execution.celery_task_id = self.request.id or ""
    execution.save(update_fields=["celery_task_id"])

    try:
        return execute_optimization(execution, run)
    except ExecutionCancelled:
        run.status = OptimizationRun.Status.CANCELLED
        run.finished_at = __import__("django.utils.timezone", fromlist=["now"]).now()
        run.save(update_fields=["status", "finished_at"])
        return {"cancelled": True}
    except Exception as exc:
        run.status = OptimizationRun.Status.FAILED
        run.error_message = str(exc)
        run.finished_at = __import__("django.utils.timezone", fromlist=["now"]).now()
        run.save(update_fields=["status", "error_message", "finished_at"])
        execution.refresh_from_db()
        if execution.status != Execution.Status.FAILED:
            mark_failed(execution, exc)
        raise
