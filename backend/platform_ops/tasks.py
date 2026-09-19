from celery import shared_task

from .maintenance import run_maintenance
from .services import snapshot_metrics


@shared_task(name="platform_ops.tasks.run_maintenance_task")
def run_maintenance_task():
    return run_maintenance()


@shared_task(name="platform_ops.tasks.snapshot_operational_metrics_task")
def snapshot_operational_metrics_task():
    snapshot = snapshot_metrics()
    return {"snapshot_id": str(snapshot.id), "captured_at": snapshot.captured_at.isoformat()}
