from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Membership, Organization, Workspace
from .serializers import OrganizationSerializer, WorkspaceSerializer


WRITE_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
]


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
            )
            .distinct()
            .order_by("name")
        )

    def perform_update(self, serializer):
        organization = self.get_object()
        role = (
            organization.memberships.filter(
                user=self.request.user,
                is_active=True,
            )
            .values_list("role", flat=True)
            .first()
        )
        if role not in [Membership.Role.OWNER, Membership.Role.ADMIN]:
            raise PermissionDenied("Solo OWNER o ADMIN puede editar la organización.")
        serializer.save()

    def perform_destroy(self, instance):
        role = (
            instance.memberships.filter(
                user=self.request.user,
                is_active=True,
            )
            .values_list("role", flat=True)
            .first()
        )
        if role != Membership.Role.OWNER:
            raise PermissionDenied("Solo OWNER puede eliminar la organización.")
        instance.delete()


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Workspace.objects.filter(
                organization__memberships__user=self.request.user,
                organization__memberships__is_active=True,
            )
            .select_related("organization")
            .distinct()
            .order_by("name")
        )

    def _assert_can_write(self, workspace):
        role = (
            workspace.organization.memberships.filter(
                user=self.request.user,
                is_active=True,
            )
            .values_list("role", flat=True)
            .first()
        )
        if role not in WRITE_ROLES:
            raise PermissionDenied("No tiene permisos de escritura sobre este workspace.")

    def perform_update(self, serializer):
        self._assert_can_write(self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_can_write(instance)
        instance.delete()
