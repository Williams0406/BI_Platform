from datetime import timedelta
from django.utils import timezone
from rest_framework import permissions,status,viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from datasources.models import DataSource
from workspaces.models import Membership
from .models import AuditLog,DestructiveChangeRequest,ResourcePermission,RetentionPolicy,WorkspaceQuota,WorkspaceUsage,WorkspacePolicy
from .serializers import AuditLogSerializer,DataSourceSecretWriteSerializer,DestructiveChangeRequestSerializer,ResourcePermissionSerializer,RetentionPolicySerializer,WorkspaceQuotaSerializer,WorkspaceUsageSerializer,WorkspacePolicySerializer
from .services import audit,get_quota,get_usage,save_datasource_secret

ADMIN_ROLES={Membership.Role.OWNER,Membership.Role.ADMIN}

def is_admin(user,workspace):
    return Membership.objects.filter(organization=workspace.organization,user=user,is_active=True,role__in=ADMIN_ROLES).exists()

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=AuditLogSerializer;permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=AuditLog.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("actor","workspace").distinct()
        workspace=self.request.query_params.get("workspace")
        return qs.filter(workspace_id=workspace) if workspace else qs

class ResourcePermissionViewSet(viewsets.ModelViewSet):
    serializer_class=ResourcePermissionSerializer;permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        return ResourcePermission.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("workspace","user").distinct()
    def perform_create(self,serializer):
        workspace=serializer.validated_data["workspace"]
        if not is_admin(self.request.user,workspace): raise PermissionDenied()
        serializer.save()
        audit(workspace,"PERMISSION_CREATE","ResourcePermission",serializer.instance.id,self.request.user)
    def perform_destroy(self,instance):
        if not is_admin(self.request.user,instance.workspace): raise PermissionDenied()
        audit(instance.workspace,"PERMISSION_DELETE","ResourcePermission",instance.id,self.request.user)
        instance.delete()

class WorkspaceGovernanceViewSet(viewsets.ViewSet):
    permission_classes=[permissions.IsAuthenticated]
    def _workspace(self,pk):
        from workspaces.models import Workspace
        return Workspace.objects.filter(id=pk,organization__memberships__user=self.request.user,organization__memberships__is_active=True).distinct().first()
    @action(detail=True,methods=["get","patch"],url_path="quota")
    def quota(self,request,pk=None):
        ws=self._workspace(pk)
        if not ws:return Response(status=404)
        q=get_quota(ws)
        if request.method=="PATCH":
            if not is_admin(request.user,ws):return Response(status=403)
            s=WorkspaceQuotaSerializer(q,data=request.data,partial=True);s.is_valid(raise_exception=True);s.save()
            audit(ws,"QUOTA_UPDATE","WorkspaceQuota",ws.id,request.user,s.validated_data)
        return Response(WorkspaceQuotaSerializer(q).data)
    @action(detail=True,methods=["get","patch"],url_path="policy")
    def policy(self,request,pk=None):
        ws=self._workspace(pk)
        if not ws:return Response(status=404)
        obj,_=WorkspacePolicy.objects.get_or_create(workspace=ws)
        if request.method=="PATCH":
            if not is_admin(request.user,ws):return Response(status=403)
            ser=WorkspacePolicySerializer(obj,data=request.data,partial=True);ser.is_valid(raise_exception=True);ser.save()
            audit(ws,"POLICY_UPDATE","WorkspacePolicy",ws.id,request.user,ser.validated_data)
        return Response(WorkspacePolicySerializer(obj).data)
    @action(detail=True,methods=["get"],url_path="members")
    def members(self,request,pk=None):
        ws=self._workspace(pk)
        if not ws:return Response(status=404)
        rows=[]
        for membership in ws.organization.memberships.filter(is_active=True).select_related("user").order_by("user__email"):
            user=membership.user
            rows.append({"id":str(user.id),"email":getattr(user,"email","") or str(user),"name":getattr(user,"get_full_name",lambda:"")() or getattr(user,"email","") or str(user),"role":membership.role})
        return Response(rows)

    @action(detail=True,methods=["get"],url_path="usage")
    def usage(self,request,pk=None):
        ws=self._workspace(pk)
        if not ws:return Response(status=404)
        return Response(WorkspaceUsageSerializer(get_usage(ws)).data)
    @action(detail=True,methods=["get","patch"],url_path="retention")
    def retention(self,request,pk=None):
        ws=self._workspace(pk)
        if not ws:return Response(status=404)
        obj,_=RetentionPolicy.objects.get_or_create(workspace=ws)
        if request.method=="PATCH":
            if not is_admin(request.user,ws):return Response(status=403)
            s=RetentionPolicySerializer(obj,data=request.data,partial=True);s.is_valid(raise_exception=True);s.save()
        return Response(RetentionPolicySerializer(obj).data)

class DataSourceSecretViewSet(viewsets.ViewSet):
    permission_classes=[permissions.IsAuthenticated]
    def _source(self,pk):
        return DataSource.objects.filter(id=pk,workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("workspace").distinct().first()
    def list(self,request):
        workspace=request.query_params.get("workspace")
        qs=DataSource.objects.filter(workspace__organization__memberships__user=request.user,workspace__organization__memberships__is_active=True).distinct()
        if workspace: qs=qs.filter(workspace_id=workspace)
        rows=[]
        for source in qs.order_by("name"):
            try: secret=source.encrypted_secret
            except Exception: secret=None
            meta=source.connection_metadata or {}
            local=source.mode==DataSource.Mode.PRIVATE_GATEWAY
            rows.append({"id":str(source.id),"name":source.name,"mode":source.mode,"engine":source.engine,"status":source.status,"credential_location":"LOCAL" if local else ("MANAGED" if secret else "NOT_CONFIGURED"),"configured":True if local else bool(secret),"key_version":getattr(secret,"key_version",None),"updated_at":getattr(secret,"updated_at",None),"gateway":meta.get("gateway_name") or meta.get("gateway"),"connection_alias":meta.get("local_connection_name") or meta.get("connection_alias")})
        return Response(rows)
    def retrieve(self,request,pk=None):
        source=self._source(pk)
        if not source:return Response(status=404)
        try: secret=source.encrypted_secret
        except Exception: secret=None
        return Response({"configured":bool(secret),"key_version":getattr(secret,"key_version",None),"updated_at":getattr(secret,"updated_at",None)})
    def create(self,request):
        source_id=request.data.get("data_source")
        source=self._source(source_id)
        if not source:return Response(status=404)
        if not is_admin(request.user,source.workspace):return Response(status=403)
        s=DataSourceSecretWriteSerializer(data=request.data);s.is_valid(raise_exception=True)
        secret=save_datasource_secret(source,s.validated_data["credentials"],request.user)
        audit(source.workspace,"SECRET_SET","DataSource",source.id,request.user)
        return Response({"configured":True,"key_version":secret.key_version,"updated_at":secret.updated_at},status=201)

class DestructiveChangeRequestViewSet(viewsets.ModelViewSet):
    serializer_class=DestructiveChangeRequestSerializer;permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        return DestructiveChangeRequest.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("workspace","requested_by","approved_by").distinct()
    def perform_create(self,serializer):
        ws=serializer.validated_data["workspace"]
        if not is_admin(self.request.user,ws):raise PermissionDenied()
        obj=serializer.save(requested_by=self.request.user,expires_at=timezone.now()+timedelta(hours=24))
        audit(ws,"DESTRUCTIVE_REQUEST","DestructiveChangeRequest",obj.id,self.request.user)
    @action(detail=True,methods=["post"],url_path="approve")
    def approve(self,request,pk=None):
        obj=self.get_object()
        if not is_admin(request.user,obj.workspace):return Response(status=403)
        if obj.status!="PENDING" or (obj.expires_at and obj.expires_at<timezone.now()):
            return Response({"detail":"Solicitud no aprobable."},status=409)
        obj.status="APPROVED";obj.approved_by=request.user;obj.approved_at=timezone.now();obj.save(update_fields=["status","approved_by","approved_at"])
        audit(obj.workspace,"DESTRUCTIVE_APPROVE","DestructiveChangeRequest",obj.id,request.user)
        return Response(DestructiveChangeRequestSerializer(obj).data)

from .models import DataCopyEvent
from .serializers import DataCopyEventSerializer

class DataCopyEventViewSet(viewsets.ModelViewSet):
    serializer_class=DataCopyEventSerializer
    permission_classes=[permissions.IsAuthenticated]
    http_method_names=["get","post","head","options"]
    def get_queryset(self):
        qs=DataCopyEvent.objects.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).select_related("source","binding","actor").distinct()
        workspace=self.request.query_params.get("workspace"); source=self.request.query_params.get("source")
        if workspace: qs=qs.filter(workspace_id=workspace)
        if source: qs=qs.filter(source_id=source)
        return qs
    def perform_create(self,serializer):
        ws=serializer.validated_data["workspace"]
        if not is_admin(self.request.user,ws): raise PermissionDenied()
        source=serializer.validated_data["source"]
        if source.workspace_id!=ws.id: raise PermissionDenied()
        serializer.save(actor=self.request.user)
