from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from datasources.models import DataAsset
from workspaces.models import Membership

from .models import AssetDependency, AssetState, ChangeEvent
from .serializers import (
    AssetDependencySerializer,
    AssetStateSerializer,
    ChangeEventSerializer,
    DependencyCreateSerializer,
)
from .services import (
    DependencyCycleError,
    create_dependency,
    lineage,
)


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def can_manage_workspace(user, workspace):
    return Membership.objects.filter(
        organization=workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()


class DependencyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            AssetDependency.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace", "upstream", "downstream")
            .distinct()
        )
        workspace = self.request.query_params.get("workspace")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return DependencyCreateSerializer
        return AssetDependencySerializer

    def create(self, request, *args, **kwargs):
        serializer = DependencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not can_manage_workspace(request.user, data["workspace"]):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            dependency, created = create_dependency(
                workspace=data["workspace"],
                upstream=data["upstream"],
                downstream=data["downstream"],
                dependency_type=data["dependency_type"],
                refresh_policy=data["refresh_policy"],
                metadata=data.get("metadata"),
            )
        except (DependencyCycleError, ValueError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            AssetDependencySerializer(dependency).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AssetStateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssetStateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            AssetState.objects.filter(
                asset__workspace__organization__memberships__user=self.request.user,
                asset__workspace__organization__memberships__is_active=True,
            )
            .select_related("asset")
            .distinct()
        )


class ChangeEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChangeEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            ChangeEvent.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("asset", "workspace")
            .distinct()
        )


class AssetLineageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        asset = (
            DataAsset.objects.filter(
                pk=pk,
                workspace__organization__memberships__user=request.user,
                workspace__organization__memberships__is_active=True,
            )
            .distinct()
            .first()
        )
        if not asset:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(lineage(asset))
