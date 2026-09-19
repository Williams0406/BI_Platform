from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from datasources.models import DataSource
from workspaces.models import Workspace

from .auth import authenticate_gateway_request
from .catalog_service import sync_gateway_catalog
from .models import GatewayDataSourceBinding, GatewayJob, GatewayRegistration
from .serializers import (
    AgentJobResultSerializer,
    GatewayBindingSerializer,
    GatewayCreateSerializer,
    GatewayEnrollSerializer,
    GatewayHeartbeatSerializer,
    GatewayJobCreateSerializer,
    GatewayJobSerializer,
    GatewayRegistrationSerializer,
    can_manage,
)
from .services import (
    bind_datasource,
    claim_next_job,
    complete_job,
    create_gateway,
    enroll_gateway,
    heartbeat,
    queue_job,
    rotate_agent_token,
    renew_enrollment,
)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


class GatewayRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GatewayRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = GatewayRegistration.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).distinct()
        workspace = self.request.query_params.get("workspace")
        return qs.filter(workspace_id=workspace) if workspace else qs

    @action(detail=False, methods=["post"], url_path="register")
    def register_gateway(self, request):
        serializer = GatewayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = Workspace.objects.filter(
            id=serializer.validated_data["workspace"],
            organization__memberships__user=request.user,
            organization__memberships__is_active=True,
        ).distinct().first()
        if not workspace:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_manage(request.user, workspace):
            return Response(status=status.HTTP_403_FORBIDDEN)

        gateway, code = create_gateway(
            workspace,
            serializer.validated_data["name"],
            request.user,
        )
        return Response(
            {
                "gateway": GatewayRegistrationSerializer(gateway).data,
                "enrollment_code": code,
                "enrollment_expires_at": gateway.enrollment_expires_at,
                "warning": "El código se muestra una sola vez.",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="renew-enrollment")
    def renew_pairing(self, request, pk=None):
        gateway = self.get_object()
        if not can_manage(request.user, gateway.workspace):
            return Response(status=status.HTTP_403_FORBIDDEN)
        code = renew_enrollment(gateway, request.user)
        return Response(
            {
                "gateway_id": str(gateway.id),
                "enrollment_code": code,
                "enrollment_expires_at": gateway.enrollment_expires_at,
                "warning": "El token anterior quedó invalidado.",
            }
        )

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        gateway = self.get_object()
        if not can_manage(request.user, gateway.workspace):
            return Response(status=status.HTTP_403_FORBIDDEN)
        gateway.status = GatewayRegistration.Status.REVOKED
        gateway.agent_token_hash = ""
        gateway.save(update_fields=["status", "agent_token_hash", "updated_at"])
        return Response({"status": gateway.status})


class GatewayBindingViewSet(viewsets.ModelViewSet):
    serializer_class = GatewayBindingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GatewayDataSourceBinding.objects.filter(
            gateway__workspace__organization__memberships__user=self.request.user,
            gateway__workspace__organization__memberships__is_active=True,
        ).select_related("gateway", "data_source").distinct()

    def perform_create(self, serializer):
        gateway = serializer.validated_data["gateway"]
        if not can_manage(self.request.user, gateway.workspace):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        binding = bind_datasource(
            gateway,
            serializer.validated_data["data_source"],
            serializer.validated_data["local_connection_name"],
        )
        serializer.instance = binding


class GatewayJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GatewayJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = GatewayJob.objects.filter(
            gateway__workspace__organization__memberships__user=self.request.user,
            gateway__workspace__organization__memberships__is_active=True,
        ).select_related("gateway", "data_source", "requested_by").distinct()
        source = self.request.query_params.get("data_source")
        if source:
            qs = qs.filter(data_source_id=source)
        return qs

    @action(detail=False, methods=["post"], url_path=r"sources/(?P<source_id>[^/.]+)/queue")
    def queue_source_job(self, request, source_id=None):
        source = DataSource.objects.filter(
            id=source_id,
            workspace__organization__memberships__user=request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related("workspace").distinct().first()
        if not source:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_manage(request.user, source.workspace):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = GatewayJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        operation = serializer.validated_data["operation"]
        if operation == GatewayJob.Operation.READ_PAGE and not source.can_read:
            return Response({"detail": "READ no habilitado."}, status=403)
        if operation in {
            GatewayJob.Operation.INSERT,
            GatewayJob.Operation.UPDATE,
            GatewayJob.Operation.DELETE,
        } and not source.can_write:
            return Response({"detail": "WRITE no habilitado."}, status=403)

        try:
            job = queue_job(
                source,
                operation,
                serializer.validated_data.get("payload", {}),
                user=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)

        return Response(GatewayJobSerializer(job).data, status=202)


class AgentEnrollView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = GatewayEnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            gateway, token = enroll_gateway(
                data["gateway_id"],
                data["enrollment_code"],
                metadata=data,
                ip_address=client_ip(request),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {
                "gateway_id": str(gateway.id),
                "agent_token": token,
                "token_version": gateway.token_version,
            }
        )


class AgentHeartbeatView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        gateway = authenticate_gateway_request(request)
        if not gateway:
            return Response(status=401)
        serializer = GatewayHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        heartbeat(gateway, serializer.validated_data, client_ip(request))
        return Response({"ok": True, "server_time": __import__("django.utils.timezone", fromlist=["now"]).now()})


class AgentClaimJobView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        gateway = authenticate_gateway_request(request)
        if not gateway:
            return Response(status=401)
        claimed = claim_next_job(gateway)
        if not claimed:
            return Response(status=204)
        job, local_connection_name = claimed
        return Response(
            {
                "job_id": str(job.id),
                "operation": job.operation,
                "payload": job.payload,
                "data_source": {
                    "id": str(job.data_source_id),
                    "engine": job.data_source.engine,
                    "local_connection_name": local_connection_name,
                },
                "lease_expires_at": job.lease_expires_at,
            }
        )


class AgentCompleteJobView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request, job_id):
        gateway = authenticate_gateway_request(request)
        if not gateway:
            return Response(status=401)
        serializer = AgentJobResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            job = complete_job(
                gateway,
                job_id,
                data["success"],
                result=data.get("result", {}),
                error_message=data.get("error_message", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)

        catalog_sync = None
        if (
            job.status == GatewayJob.Status.SUCCESS
            and job.operation == GatewayJob.Operation.CATALOG
        ):
            catalog = (job.result or {}).get("tables", [])
            catalog_sync = sync_gateway_catalog(
                job.data_source,
                catalog,
                created_by=job.requested_by or job.data_source.created_by,
            )
            from .models import GatewayImportRequest
            req=GatewayImportRequest.objects.filter(catalog_job=job).first()
            if req:
                wanted=req.selected_tables if req.scope==GatewayImportRequest.Scope.SELECTED_TABLES else []
                chosen=[]
                for table in catalog:
                    key=f"{table.get('schema','')}.{table.get('name') or table.get('table','')}".strip('.')
                    if not wanted or key in wanted or (table.get('name') or table.get('table')) in wanted:
                        chosen.append(key)
                req.status=GatewayImportRequest.Status.IMPORTING
                req.progress=10
                req.table_progress={k:{"status":"QUEUED","progress":0} for k in chosen}
                req.save(update_fields=["status","progress","table_progress","updated_at"])
                # Data pages are intentionally queued as internal jobs; users never author payload JSON.
                for table in catalog:
                    name=table.get('name') or table.get('table')
                    schema=table.get('schema','')
                    key=f"{schema}.{name}".strip('.')
                    if key in chosen:
                        queue_job(job.data_source,GatewayJob.Operation.READ_PAGE,{"schema":schema,"table":name,"limit":1000,"offset":0,"import_request":str(req.id)},user=req.requested_by)

        if job.operation == GatewayJob.Operation.READ_PAGE and (job.payload or {}).get("import_request"):
            from .models import GatewayImportRequest
            req=GatewayImportRequest.objects.filter(id=job.payload.get("import_request")).first()
            if req:
                key=f"{job.payload.get('schema','')}.{job.payload.get('table','')}".strip('.')
                progress=dict(req.table_progress or {})
                progress[key]={"status":"IMPORTED_PAGE" if job.status==GatewayJob.Status.SUCCESS else "FAILED","progress":100 if job.status==GatewayJob.Status.SUCCESS else 0,"rows":len((job.result or {}).get("rows",[]))}
                req.table_progress=progress
                done=sum(1 for x in progress.values() if x.get("status") in {"IMPORTED_PAGE","FAILED"})
                req.progress=min(100,10+int(90*done/max(len(progress),1)))
                if done>=len(progress): req.status=GatewayImportRequest.Status.SUCCEEDED if all(x.get("status")=="IMPORTED_PAGE" for x in progress.values()) else GatewayImportRequest.Status.FAILED
                req.save(update_fields=["table_progress","progress","status","updated_at"])
        return Response(
            {
                "ok": True,
                "status": job.status,
                "catalog_sync": catalog_sync,
            }
        )


class AgentRotateTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        gateway = authenticate_gateway_request(request)
        if not gateway:
            return Response(status=401)
        token = rotate_agent_token(gateway, client_ip(request))
        return Response(
            {
                "agent_token": token,
                "token_version": gateway.token_version,
                "warning": "Reemplace el token anterior inmediatamente.",
            }
        )

from .models import GatewayImportRequest
from .serializers import GatewayImportRequestSerializer

class GatewayImportRequestViewSet(viewsets.ModelViewSet):
    serializer_class=GatewayImportRequestSerializer
    permission_classes=[permissions.IsAuthenticated]
    http_method_names=["get","post","head","options"]
    def get_queryset(self):
        qs=GatewayImportRequest.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("data_source","catalog_job").distinct()
        workspace=self.request.query_params.get("workspace")
        if workspace: qs=qs.filter(workspace_id=workspace)
        return qs
    def perform_create(self,serializer):
        source=serializer.validated_data["data_source"]
        if not can_manage(self.request.user,source.workspace):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        if source.mode!=DataSource.Mode.PRIVATE_GATEWAY: raise ValueError("DataSource no es PRIVATE_GATEWAY")
        obj=serializer.save(workspace=source.workspace,requested_by=self.request.user,status=GatewayImportRequest.Status.DISCOVERING)
        try:
            from governance.models import DataCopyEvent
            DataCopyEvent.objects.create(workspace=source.workspace,source=source,kind=DataCopyEvent.Kind.INITIAL_SNAPSHOT,title="Initial Platform copy",summary="Private source import started",detail={"scope":obj.scope,"selected_tables":obj.selected_tables,"gateway_import_request":str(obj.id)},version=1,actor=self.request.user)
        except Exception:
            pass
        job=queue_job(source,GatewayJob.Operation.CATALOG,{"include_views":True},user=self.request.user)
        obj.catalog_job=job;obj.save(update_fields=["catalog_job","updated_at"])
