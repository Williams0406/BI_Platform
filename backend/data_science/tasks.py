from celery import shared_task
from execution.models import Execution
from execution.services import mark_failed, ExecutionCancelled
from .ml_services import batch_inference, train_model
from .models import DatasetDefinition, ModelRun, ModelVersion, PythonTransformation
from .python_services import execute_python_transformation

@shared_task(bind=True, name="data_science.tasks.run_python_transformation_task")
def run_python_transformation_task(self, execution_id, transformation_id):
    execution=Execution.objects.get(id=execution_id)
    transformation=PythonTransformation.objects.get(id=transformation_id)
    if execution.status==Execution.Status.CANCELLED: return {"cancelled":True}
    execution.celery_task_id=self.request.id or ""; execution.save(update_fields=["celery_task_id"])
    try: return execute_python_transformation(execution,transformation)
    except Exception as exc:
        execution.refresh_from_db()
        if execution.status!=Execution.Status.FAILED: mark_failed(execution,exc)
        raise

@shared_task(bind=True, name="data_science.tasks.train_model_task")
def train_model_task(self, execution_id, model_run_id):
    execution=Execution.objects.get(id=execution_id)
    model_run=ModelRun.objects.select_related("model","model__dataset","model__target").get(id=model_run_id)
    if execution.status==Execution.Status.CANCELLED:
        model_run.status=ModelRun.Status.CANCELLED; model_run.save(update_fields=["status"]); return {"cancelled":True}
    execution.celery_task_id=self.request.id or ""; execution.save(update_fields=["celery_task_id"])
    try: return train_model(execution,model_run)
    except ExecutionCancelled:
        model_run.status=ModelRun.Status.CANCELLED; model_run.finished_at=__import__("django.utils.timezone",fromlist=["now"]).now(); model_run.save(update_fields=["status","finished_at"]); return {"cancelled":True}
    except Exception as exc:
        model_run.status=ModelRun.Status.FAILED; model_run.error_message=str(exc); model_run.save(update_fields=["status","error_message"])
        execution.refresh_from_db()
        if execution.status!=Execution.Status.FAILED: mark_failed(execution,exc)
        raise

@shared_task(bind=True, name="data_science.tasks.batch_inference_task")
def batch_inference_task(self, execution_id, model_version_id, dataset_id, requested_by_id=None):
    execution=Execution.objects.get(id=execution_id)
    version=ModelVersion.objects.select_related("model","model__workspace","model__data_asset").get(id=model_version_id)
    dataset=DatasetDefinition.objects.select_related("source_table","source_table__data_asset").get(id=dataset_id)
    if execution.status==Execution.Status.CANCELLED: return {"cancelled":True}
    execution.celery_task_id=self.request.id or ""; execution.save(update_fields=["celery_task_id"])
    requested_by=None
    if requested_by_id:
        from django.contrib.auth import get_user_model
        requested_by=get_user_model().objects.filter(id=requested_by_id).first()
    try: return batch_inference(execution,version,dataset,requested_by=requested_by)
    except ExecutionCancelled:
        return {"cancelled":True}
    except Exception as exc:
        execution.refresh_from_db()
        if execution.status!=Execution.Status.FAILED: mark_failed(execution,exc)
        raise
