from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from workspaces.models import Membership

from .models import DataAsset, DataSource
from .serializers import DataAssetSerializer, DataSourceSerializer


WRITE_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
]


def can_write_workspace(user, workspace):
    return Membership.objects.filter(
        organization=workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()


class DataSourceViewSet(viewsets.ModelViewSet):
    serializer_class = DataSourceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            DataSource.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace", "workspace__organization")
            .distinct()
            .order_by("name")
        )

        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        return queryset

    def perform_update(self, serializer):
        obj = self.get_object()
        if not can_write_workspace(self.request.user, obj.workspace):
            raise PermissionDenied("No tiene permisos de escritura.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_write_workspace(self.request.user, instance.workspace):
            raise PermissionDenied("No tiene permisos de escritura.")
        instance.delete()


class DataAssetViewSet(viewsets.ModelViewSet):
    serializer_class = DataAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            DataAsset.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace", "data_source")
            .distinct()
            .order_by("name")
        )

        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        asset_type = self.request.query_params.get("asset_type")
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)

        return queryset

    def perform_update(self, serializer):
        obj = self.get_object()
        if not can_write_workspace(self.request.user, obj.workspace):
            raise PermissionDenied("No tiene permisos de escritura.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_write_workspace(self.request.user, instance.workspace):
            raise PermissionDenied("No tiene permisos de escritura.")
        instance.delete()

from .models import SourceBinding, PublishPlan, WritebackPolicy
from .serializers import SourceBindingSerializer, PublishPlanSerializer, WritebackPolicySerializer

class WorkspaceGovernedViewSet(viewsets.ModelViewSet):
    permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=self.queryset.filter(workspace__organization__memberships__user=self.request.user,workspace__organization__memberships__is_active=True).distinct()
        workspace_id=self.request.query_params.get("workspace"); source_id=self.request.query_params.get("source")
        if workspace_id: qs=qs.filter(workspace_id=workspace_id)
        if source_id: qs=qs.filter(source_id=source_id)
        return qs
    def perform_update(self,serializer):
        obj=self.get_object()
        if not can_write_workspace(self.request.user,obj.workspace): raise PermissionDenied("No tiene permisos de escritura.")
        serializer.save()
    def perform_destroy(self,instance):
        if not can_write_workspace(self.request.user,instance.workspace): raise PermissionDenied("No tiene permisos de escritura.")
        instance.delete()

class SourceBindingViewSet(WorkspaceGovernedViewSet):
    queryset=SourceBinding.objects.select_related("workspace","source","platform_asset")
    serializer_class=SourceBindingSerializer
class PublishPlanViewSet(WorkspaceGovernedViewSet):
    queryset=PublishPlan.objects.select_related("workspace","source","binding")
    serializer_class=PublishPlanSerializer
class WritebackPolicyViewSet(WorkspaceGovernedViewSet):
    queryset=WritebackPolicy.objects.select_related("workspace","source")
    serializer_class=WritebackPolicySerializer
