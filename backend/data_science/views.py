from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from execution.models import Execution
from execution.services import create_execution
from .models import DatasetDefinition, ModelDefinition, ModelRun, ModelVersion, PredictionAsset, PythonTransformation
from .serializers import DatasetDefinitionSerializer, InferenceRequestSerializer, ModelDefinitionSerializer, ModelRunSerializer, ModelVersionSerializer, PredictionAssetSerializer, PythonTransformationInputSerializer, PythonTransformationSerializer, can_build
from .tasks import batch_inference_task, run_python_transformation_task, train_model_task

class PythonTransformationViewSet(viewsets.ModelViewSet):
    serializer_class=PythonTransformationSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=PythonTransformation.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).prefetch_related("inputs__asset").distinct()
        workspace=self.request.query_params.get("workspace"); return qs.filter(workspace_id=workspace) if workspace else qs
    @action(detail=True,methods=["post"],url_path="inputs")
    def add_input(self,request,pk=None):
        transformation=self.get_object()
        if not can_build(request.user,transformation.workspace): return Response(status=status.HTTP_403_FORBIDDEN)
        serializer=PythonTransformationInputSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        asset=serializer.validated_data["asset"]
        if asset.workspace_id!=transformation.workspace_id: return Response({"detail":"Input y transformación deben pertenecer al mismo workspace."},status=status.HTTP_400_BAD_REQUEST)
        item=serializer.save(transformation=transformation)
        return Response(PythonTransformationInputSerializer(item).data,status=status.HTTP_201_CREATED)
    @action(detail=True,methods=["post"],url_path="run")
    def run_transformation(self,request,pk=None):
        transformation=self.get_object()
        if not can_build(request.user,transformation.workspace): return Response(status=status.HTTP_403_FORBIDDEN)
        execution=create_execution(workspace=transformation.workspace,object_type=Execution.ObjectType.PYTHON_TRANSFORMATION,object_id=transformation.id,queue="python",requested_by=request.user)
        result=run_python_transformation_task.apply_async(args=[str(execution.id),str(transformation.id)],queue="python")
        execution.celery_task_id=result.id or ""; execution.save(update_fields=["celery_task_id"])
        return Response({"execution_id":str(execution.id),"celery_task_id":execution.celery_task_id,"status":execution.status},status=status.HTTP_202_ACCEPTED)

class DatasetDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class=DatasetDefinitionSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=DatasetDefinition.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("source_table","workspace").distinct()
        workspace=self.request.query_params.get("workspace"); return qs.filter(workspace_id=workspace) if workspace else qs

class ModelDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class=ModelDefinitionSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=ModelDefinition.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("dataset","target","data_asset","workspace").prefetch_related("features").distinct()
        workspace=self.request.query_params.get("workspace"); return qs.filter(workspace_id=workspace) if workspace else qs
    @action(detail=True,methods=["post"],url_path="train")
    def train(self,request,pk=None):
        model=self.get_object()
        if not can_build(request.user,model.workspace): return Response(status=status.HTTP_403_FORBIDDEN)
        model_run=ModelRun.objects.create(model=model,parameters_snapshot=dict(model.parameters or {}))
        execution=create_execution(workspace=model.workspace,object_type=Execution.ObjectType.ML_TRAINING,object_id=model.id,queue="ml",requested_by=request.user,parameters={"model_run_id":str(model_run.id)})
        model_run.execution_id=execution.id; model_run.save(update_fields=["execution_id"])
        result=train_model_task.apply_async(args=[str(execution.id),str(model_run.id)],queue="ml")
        execution.celery_task_id=result.id or ""; execution.save(update_fields=["celery_task_id"])
        return Response({"model_run_id":str(model_run.id),"execution_id":str(execution.id),"status":model_run.status},status=status.HTTP_202_ACCEPTED)

class ModelRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=ModelRunSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=ModelRun.objects.filter(model__workspace__organization__memberships__user=self.request.user,model__workspace__organization__memberships__is_active=True).select_related("model").distinct()
        model_id=self.request.query_params.get("model"); return qs.filter(model_id=model_id) if model_id else qs

class ModelVersionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=ModelVersionSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=ModelVersion.objects.filter(model__workspace__organization__memberships__user=self.request.user,model__workspace__organization__memberships__is_active=True).select_related("model","run").distinct()
        model_id=self.request.query_params.get("model"); return qs.filter(model_id=model_id) if model_id else qs
    @action(detail=True,methods=["post"],url_path="infer")
    def infer(self,request,pk=None):
        version=self.get_object(); serializer=InferenceRequestSerializer(data=request.data); serializer.is_valid(raise_exception=True); dataset=serializer.validated_data["dataset"]
        if dataset.workspace_id!=version.model.workspace_id: return Response({"detail":"Dataset y modelo deben pertenecer al mismo workspace."},status=status.HTTP_400_BAD_REQUEST)
        if not can_build(request.user,version.model.workspace): return Response(status=status.HTTP_403_FORBIDDEN)
        execution=create_execution(workspace=version.model.workspace,object_type=Execution.ObjectType.ML_INFERENCE,object_id=version.id,queue="ml",requested_by=request.user,parameters={"dataset_id":str(dataset.id)})
        result=batch_inference_task.apply_async(args=[str(execution.id),str(version.id),str(dataset.id),str(request.user.id)],queue="ml")
        execution.celery_task_id=result.id or ""; execution.save(update_fields=["celery_task_id"])
        return Response({"execution_id":str(execution.id),"status":execution.status},status=status.HTTP_202_ACCEPTED)

class PredictionAssetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=PredictionAssetSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        return PredictionAsset.objects.filter(model_version__model__workspace__organization__memberships__user=self.request.user,model_version__model__workspace__organization__memberships__is_active=True).select_related("model_version","source_dataset","data_asset").distinct()
