from celery import shared_task

from .models import ChangeEvent
from .services import propagate_change


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="dependencies.tasks.propagate_asset_change_task",
)
def propagate_asset_change_task(self, event_id):
    event = ChangeEvent.objects.select_related("asset", "workspace").get(id=event_id)
    return propagate_change(event)
