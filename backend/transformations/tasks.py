from celery import shared_task

from execution.models import Execution
from execution.services import mark_failed

from .services import execute_sql_transformation


@shared_task(
    bind=True,
    autoretry_for=(),
    name="transformations.tasks.run_sql_transformation_task",
)
def run_sql_transformation_task(self, execution_id):
    execution = Execution.objects.get(id=execution_id)

    if execution.status == Execution.Status.CANCELLED:
        return {"cancelled": True}

    execution.celery_task_id = self.request.id or ""
    execution.save(update_fields=["celery_task_id"])

    try:
        return execute_sql_transformation(execution)
    except Exception as exc:
        execution.refresh_from_db()
        if execution.status != Execution.Status.FAILED:
            mark_failed(execution, exc)
        raise
