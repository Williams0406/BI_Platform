from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from workspaces.models import Membership
from governance.services import GovernanceError, mark_destructive_executed, require_approved_destructive_change

from .managed_serializers import ManagedTableCreateSerializer
from .managed_services import create_managed_table, delete_managed_table
from .models import TableAsset
from .serializers import TableAssetSerializer


WRITE_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
]


def can_write_table(user, table_asset):
    return Membership.objects.filter(
        organization=table_asset.data_source.workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()


class ManagedTableCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ManagedTableCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = create_managed_table(
                workspace=data["workspace"],
                name=data["name"],
                display_name=data.get("display_name", ""),
                fields=data["fields"],
                primary_key=data.get("primary_key", []),
                foreign_keys=data.get("foreign_keys", []),
                user=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            TableAssetSerializer(result.table_asset).data,
            status=status.HTTP_201_CREATED,
        )


class ManagedTableDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        table = (
            TableAsset.objects.filter(
                pk=pk,
                data_source__workspace__organization__memberships__user=request.user,
                data_source__workspace__organization__memberships__is_active=True,
            )
            .select_related(
                "data_source",
                "data_source__workspace",
                "data_source__workspace__organization",
                "data_asset",
            )
            .distinct()
            .first()
        )
        if not table:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not can_write_table(request.user, table):
            return Response(
                {"detail": "No tiene permisos para eliminar esta tabla."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            approval = require_approved_destructive_change(
                table.data_source.workspace,
                "DELETE_MANAGED_TABLE",
                "TableAsset",
                table.id,
            )
            delete_managed_table(table)
            mark_destructive_executed(approval, request.user)
        except GovernanceError as exc:
            return Response(
                {"detail": str(exc), "requires_approval": True},
                status=status.HTTP_409_CONFLICT,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
