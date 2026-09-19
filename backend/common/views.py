import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger("platform.health")


@api_view(["GET"])
@permission_classes([AllowAny])
def root(request):
    return Response(
        {
            "service": "business-intelligence-platform-api",
            "status": "ok",
            "api_version": "v1",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health_live(request):
    return Response({"status": "ok", "service": "api", "check": "liveness"})


@api_view(["GET"])
@permission_classes([AllowAny])
def health_ready(request):
    checks = {}
    ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "available"
    except Exception as exc:
        logger.exception("Readiness database check failed")
        checks["database"] = exc.__class__.__name__
        ok = False

    if settings.OPS_READY_CHECK_REDIS:
        try:
            cache.set("health:ready", "ok", 5)
            if cache.get("health:ready") != "ok":
                raise RuntimeError("cache roundtrip failed")
            checks["redis"] = "available"
        except Exception as exc:
            checks["redis"] = exc.__class__.__name__
            ok = False

    if settings.OPS_READY_CHECK_STORAGE:
        try:
            from platform_ops.storage import healthcheck
            result = healthcheck()
            checks["storage"] = result
            if not result.get("ok"):
                ok = False
        except Exception as exc:
            checks["storage"] = {"ok": False, "detail": exc.__class__.__name__}
            ok = False

    return Response(
        {"status": "ok" if ok else "error", "checks": checks},
        status=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import ScriptBlock, ScriptArtifact, ComputeTarget, PythonEnvironment, EnvironmentPackage
from .script_analysis import analyze

class ScriptArtifactSerializer(serializers.ModelSerializer):
    class Meta: model=ScriptArtifact; fields="__all__"
class ScriptBlockSerializer(serializers.ModelSerializer):
    artifacts=ScriptArtifactSerializer(many=True,read_only=True)
    class Meta:
        model=ScriptBlock; fields=['id','workspace','name','language','purpose','code','context','linked_object_type','linked_object_id','status','created_by','created_at','updated_at','artifacts']; read_only_fields=['created_by','created_at','updated_at','artifacts']
    def create(self,validated_data):
        obj=ScriptBlock.objects.create(created_by=self.context['request'].user,**validated_data)
        result=analyze(obj.language,obj.code)
        for a in result.get('artifacts',[]): ScriptArtifact.objects.create(script_block=obj,artifact_type=a['type'],name=a.get('name',''),metadata=a)
        return obj
    def update(self,instance,validated_data):
        instance=super().update(instance,validated_data)
        if 'code' in validated_data or 'language' in validated_data:
            instance.artifacts.all().delete()
            result=analyze(instance.language,instance.code)
            for a in result.get('artifacts',[]): ScriptArtifact.objects.create(script_block=instance,artifact_type=a['type'],name=a.get('name',''),metadata=a)
        return instance
class ScriptBlockViewSet(viewsets.ModelViewSet):
    serializer_class=ScriptBlockSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=ScriptBlock.objects.select_related('workspace','created_by').prefetch_related('artifacts'); workspace=self.request.query_params.get('workspace'); return qs.filter(workspace_id=workspace) if workspace else qs.none()
    @action(detail=False,methods=['post'])
    def analyze(self,request): return Response(analyze(request.data.get('language','PYTHON'),request.data.get('code','')))
    @action(detail=True,methods=['post'],url_path='promote-metric')
    def promote_metric(self,request,pk=None):
        block=self.get_object(); artifact_id=request.data.get('artifact_id')
        source=block.artifacts.filter(id=artifact_id,artifact_type=ScriptArtifact.Type.VARIABLE).first()
        if not source: return Response({'detail':'Variable artifact not found.'},status=404)
        metric,created=ScriptArtifact.objects.get_or_create(script_block=block,artifact_type=ScriptArtifact.Type.MEASURE,name=source.name,defaults={'metadata':{'source_variable_artifact':str(source.id),'expression':source.metadata.get('expression',''),'promoted':True}})
        return Response(ScriptArtifactSerializer(metric).data,status=201 if created else 200)

class ComputeTargetSerializer(serializers.ModelSerializer):
    class Meta: model=ComputeTarget; fields='__all__'
class ComputeTargetViewSet(viewsets.ModelViewSet):
    serializer_class=ComputeTargetSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self): return ComputeTarget.objects.filter(workspace_id=self.request.query_params.get('workspace')) if self.request.query_params.get('workspace') else ComputeTarget.objects.none()
class EnvironmentPackageSerializer(serializers.ModelSerializer):
    class Meta: model=EnvironmentPackage; fields='__all__'
class PythonEnvironmentSerializer(serializers.ModelSerializer):
    packages=EnvironmentPackageSerializer(many=True,read_only=True)
    class Meta: model=PythonEnvironment; fields='__all__'
class PythonEnvironmentViewSet(viewsets.ModelViewSet):
    serializer_class=PythonEnvironmentSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self): return PythonEnvironment.objects.filter(workspace_id=self.request.query_params.get('workspace')).prefetch_related('packages') if self.request.query_params.get('workspace') else PythonEnvironment.objects.none()
class EnvironmentPackageViewSet(viewsets.ModelViewSet):
    serializer_class=EnvironmentPackageSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=EnvironmentPackage.objects.all(); env=self.request.query_params.get('environment'); return qs.filter(environment_id=env) if env else qs.none()
