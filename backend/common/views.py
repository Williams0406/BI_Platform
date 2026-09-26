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
    def destroy(self, request, *args, **kwargs):
        from .code_deletion import delete_code_and_measures
        block = self.get_object()
        return Response(delete_code_and_measures(workspace_id=block.workspace_id, script_id=block.id))
    def get_queryset(self):
        # Detail actions (PATCH/DELETE) do not carry the workspace query parameter.
        # Always scope scripts to workspaces the current user can access, then apply
        # the optional workspace filter used by the notebook list endpoint.
        qs=(ScriptBlock.objects
            .select_related('workspace','created_by')
            .prefetch_related('artifacts')
            .filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .distinct())
        workspace=self.request.query_params.get('workspace')
        return qs.filter(workspace_id=workspace) if workspace else qs
    @action(detail=False,methods=['post'])
    def analyze(self,request): return Response(analyze(request.data.get('language','PYTHON'),request.data.get('code','')))
    @action(detail=True,methods=['post'],url_path='execute')
    def execute(self,request,pk=None):
        from .notebook_execution import execute_block
        block=self.get_object()
        try:
            output=execute_block(block, request.data.get("environment_id"))
            # Trained estimator variables are registered as Data Science model versions
            # as part of a successful Python notebook execution.
            if (block.language or "").upper()=="PYTHON":
                # DataFrames directly assigned by the current cell are materialized
                # in Data automatically. The runtime hands us the already-computed
                # frame, avoiding a second notebook execution.
                captured_frames=output.pop("_captured_dataframes",{})
                auto_published=[]
                if captured_frames:
                    from .python_publish import publish_python_dataframe
                    for variable_name,frame in captured_frames.items():
                        auto_published.append(publish_python_dataframe(block,request.user,variable_name,frame,variable_name))
                    output["auto_published"]=auto_published
                ml_vars=[v for v in (output.get("variables") or []) if v.get("kind")=="ml_model"]
                registrations=[]
                if ml_vars:
                    from .notebook_execution import execute_python
                    from data_science.code_registration import register_code_model
                    for variable in ml_vars:
                        captured=execute_python(block,request.data.get("environment_id"),capture_variable=variable["name"])
                        registrations.append(register_code_model(block,request.user,captured,variable["name"]))
                    output["ml_registrations"]=registrations
                opt_vars=[v for v in (output.get("variables") or []) if v.get("kind")=="optimization_model" and not v.get("error")]
                opt_registrations=[]
                if opt_vars:
                    from .notebook_execution import execute_python
                    from optimization.code_registration import register_code_optimization
                    for variable in opt_vars:
                        captured=execute_python(block,request.data.get("environment_id"),capture_variable=variable["name"])
                        opt_registrations.append(register_code_optimization(block,request.user,captured["spec"],variable["name"]))
                    output["optimization_registrations"]=opt_registrations
            context={**(block.context or {}),'notebook_output':output}
            if output.get('environment'): context['python_environment_id']=output['environment']['id']
            block.context=context; block.save(update_fields=['context','updated_at'])
            return Response(output)
        except Exception as exc:
            return Response({'detail':str(exc)},status=400)
    @action(detail=True,methods=['post'],url_path='publish')
    def publish(self,request,pk=None):
        from .script_publish import publish_block
        block=self.get_object()
        try:
            return Response(publish_block(block,request.user))
        except (ValueError, Exception) as exc:
            return Response({'detail':str(exc)},status=400)
    @action(detail=True,methods=['post'],url_path='publish-python-variable')
    def publish_python_variable(self,request,pk=None):
        from .python_publish import publish_python_variable
        block=self.get_object()
        variable=(request.data.get('variable') or '').strip()
        if not variable: return Response({'detail':'Variable is required.'},status=400)
        try:
            result=publish_python_variable(block,request.user,variable,request.data.get('name'),request.data.get('environment_id'))
            return Response(result)
        except Exception as exc:
            return Response({'detail':str(exc)},status=400)

    @action(detail=True,methods=['post'],url_path='register-ml-model')
    def register_ml_model(self,request,pk=None):
        from .notebook_execution import execute_python
        from data_science.code_registration import register_code_model
        block=self.get_object(); variable=(request.data.get('variable') or '').strip()
        if not variable: return Response({'detail':'Variable is required.'},status=400)
        try:
            captured=execute_python(block,request.data.get('environment_id'),capture_variable=variable)
            return Response(register_code_model(block,request.user,captured,request.data.get('name')))
        except Exception as exc:
            return Response({'detail':str(exc)},status=400)

    @action(detail=True,methods=['post'],url_path='register-optimization-model')
    def register_optimization_model(self,request,pk=None):
        from .notebook_execution import execute_python
        from optimization.code_registration import register_code_optimization
        block=self.get_object(); variable=(request.data.get('variable') or '').strip()
        if not variable: return Response({'detail':'Variable is required.'},status=400)
        try:
            captured=execute_python(block,request.data.get('environment_id'),capture_variable=variable)
            if captured.get('kind')!='optimization_model': return Response({'detail':'Variable is not an optimization model.'},status=400)
            return Response(register_code_optimization(block,request.user,captured['spec'],variable))
        except Exception as exc:
            return Response({'detail':str(exc)},status=400)

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
    PACKAGE_ALIASES = {"sklearn": "scikit-learn"}
    class Meta: model=EnvironmentPackage; fields='__all__'
    def validate_name(self, value):
        name=(value or "").strip()
        return self.PACKAGE_ALIASES.get(name.lower(), name)
class PythonEnvironmentSerializer(serializers.ModelSerializer):
    packages=EnvironmentPackageSerializer(many=True,read_only=True)
    class Meta: model=PythonEnvironment; fields='__all__'
class PythonEnvironmentViewSet(viewsets.ModelViewSet):
    serializer_class=PythonEnvironmentSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self): return PythonEnvironment.objects.filter(workspace_id=self.request.query_params.get('workspace')).prefetch_related('packages')[:1] if self.request.query_params.get('workspace') else PythonEnvironment.objects.none()
    def perform_create(self, serializer):
        from django.db import transaction
        from rest_framework.exceptions import ValidationError
        from .environment_tasks import install_environment_package
        workspace=serializer.validated_data["workspace"]
        if PythonEnvironment.objects.filter(workspace=workspace).exists():
            raise ValidationError({"workspace":"This workspace already has its Python environment."})
        env=serializer.save(name="Python",status="ACTIVE")
        # Workspace tables are exposed to Code as pandas DataFrames. New
        # environments therefore receive the two base analytical dependencies.
        for name in ("pandas","numpy"):
            package,_=EnvironmentPackage.objects.get_or_create(environment=env,name=name,defaults={"status":"REQUESTED","source":"PYPI"})
            transaction.on_commit(lambda package_id=str(package.id): install_environment_package.apply_async(args=[package_id],queue="python"))
class EnvironmentPackageViewSet(viewsets.ModelViewSet):
    serializer_class=EnvironmentPackageSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=EnvironmentPackage.objects.all(); env=self.request.query_params.get('environment'); return qs.filter(environment_id=env) if env else qs.none()
    def perform_create(self, serializer):
        from django.db import transaction
        from .environment_tasks import install_environment_package
        package=serializer.save(status="REQUESTED",source="PYPI")
        transaction.on_commit(lambda: install_environment_package.apply_async(args=[str(package.id)],queue="python"))
    @action(detail=True,methods=["post"],url_path="retry-install")
    def retry_install(self,request,pk=None):
        from .environment_tasks import install_environment_package
        package=self.get_object()
        if package.name.lower()=="sklearn":
            canonical=EnvironmentPackage.objects.filter(environment=package.environment,name__iexact="scikit-learn").exclude(pk=package.pk).first()
            if canonical:
                package.delete(); package=canonical
            else:
                package.name="scikit-learn"
        if package.status == "INSTALLING": return Response({"detail":"Package installation is already running."},status=202)
        package.status="REQUESTED"; package.log=""; package.save(update_fields=["name","status","log","updated_at"])
        install_environment_package.apply_async(args=[str(package.id)],queue="python")
        return Response({"detail":"Package installation queued.","id":str(package.id)},status=202)
    def destroy(self, request, *args, **kwargs):
        from .environment_tasks import uninstall_environment_package
        package=self.get_object()
        if package.status == "UNINSTALLING": return Response({"detail":"Package uninstall already queued."},status=202)
        package.status="UNINSTALLING"; package.save(update_fields=["status","updated_at"])
        uninstall_environment_package.apply_async(args=[str(package.id)],queue="python")
        return Response({"detail":"Package uninstall queued.","id":str(package.id)},status=202)
    @action(detail=False,methods=["post"],url_path="sync-installed")
    def sync_installed(self,request):
        from .environment_services import installed_environment_packages, package_health_check
        env_id=request.data.get("environment")
        if not env_id: return Response({"detail":"environment is required"},status=400)
        try: env=PythonEnvironment.objects.get(pk=env_id)
        except PythonEnvironment.DoesNotExist: return Response({"detail":"Environment not found."},status=404)
        # Only expose packages that are actually installed in this isolated environment.
        found=installed_environment_packages(env)
        created=updated=0
        for item in found:
            name=item.get("name","").strip()
            if not name: continue
            healthy,verified_version,health_log=package_health_check(env,name,check_dependencies=False)
            real_version=verified_version or item.get("version","")
            real_status="INSTALLED" if healthy else "FAILED"
            obj,was_created=EnvironmentPackage.objects.get_or_create(environment=env,name=name,defaults={"source":"PYPI","status":real_status,"installed_version":real_version,"log":health_log})
            if was_created: created+=1
            else:
                changed=False
                if obj.status!=real_status: obj.status=real_status; changed=True
                if obj.installed_version!=real_version: obj.installed_version=real_version; changed=True
                if obj.log!=("" if healthy else health_log): obj.log="" if healthy else health_log; changed=True
                if changed: obj.save(update_fields=["status","installed_version","log","updated_at"]); updated+=1
        return Response({"created":created,"updated":updated,"count":len(found)})

    @action(detail=False,methods=["get"],url_path="search-pypi")
    def search_pypi(self,request):
        from .environment_services import search_pypi
        q=request.query_params.get("q","").strip()
        if len(q)<2: return Response([])
        try: return Response(search_pypi(q))
        except Exception as exc: return Response({"detail":f"PyPI search unavailable: {exc}"},status=503)
    @action(detail=False,methods=["get"],url_path="pypi-package")
    def pypi_package(self,request):
        from .environment_services import pypi_package
        name=request.query_params.get("name","").strip()
        if not name: return Response({"detail":"name is required"},status=400)
        try: return Response(pypi_package(name))
        except Exception as exc: return Response({"detail":f"Package not found: {exc}"},status=404)
