from celery import shared_task

from .models import Execution
from .services import mark_failed, mark_running, mark_success


@shared_task(bind=True, name="execution.tasks.execute_job")
def execute_job(self, execution_id):
    execution = Execution.objects.get(id=execution_id)

    if execution.status == Execution.Status.CANCELLED:
        return {"cancelled": True}

    execution.celery_task_id = self.request.id or ""
    execution.save(update_fields=["celery_task_id"])

    try:
        mark_running(execution)
        result = {
            "detail": "Generic execution placeholder.",
            "object_type": execution.object_type,
        }
        mark_success(execution, result)
        return result
    except Exception as exc:
        mark_failed(execution, exc)
        raise
