from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from datasources.models import DataSource

from .exceptions import ConnectorError
from .permissions import user_can_manage_datasource
from .registry import build_connector
from .serializers import (
    CatalogRequestSerializer,
    ReadPageRequestSerializer,
    RuntimeCredentialsSerializer,
)


def get_accessible_source(user, pk):
    return (
        DataSource.objects.filter(
            pk=pk,
            workspace__organization__memberships__user=user,
            workspace__organization__memberships__is_active=True,
        )
        .select_related("workspace", "workspace__organization")
        .distinct()
        .first()
    )


def secret_free_validated_data(validated_data):
    return {
        key: value
        for key, value in validated_data.items()
        if key not in {"schemas", "include_views", "schema", "table", "columns", "limit", "offset", "cursor_field", "cursor_gt"}
    }


class DataSourceTestConnectionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        data_source = get_accessible_source(request.user, pk)
        if not data_source:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not user_can_manage_datasource(request.user, data_source):
            return Response(
                {"detail": "No tiene permisos para administrar esta fuente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RuntimeCredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            connector = build_connector(
                data_source,
                serializer.validated_data,
            )
            return Response(connector.test_connection())
        except ConnectorError as exc:
            return Response(
                {"ok": False, "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DataSourceCatalogPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        data_source = get_accessible_source(request.user, pk)
        if not data_source:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not user_can_manage_datasource(request.user, data_source):
            return Response(
                {"detail": "No tiene permisos para administrar esta fuente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CatalogRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        runtime = secret_free_validated_data(data)
        try:
            connector = build_connector(data_source, runtime)
            catalog = connector.introspect_catalog(
                schemas=data.get("schemas"),
                include_views=data.get("include_views", True),
            )
            return Response(
                {
                    "data_source": str(data_source.id),
                    "engine": data_source.engine,
                    "count": len(catalog),
                    "tables": [item.to_dict() for item in catalog],
                }
            )
        except ConnectorError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DataSourceReadPageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        data_source = get_accessible_source(request.user, pk)
        if not data_source:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not data_source.can_read:
            return Response(
                {"detail": "La fuente no tiene capacidad READ habilitada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReadPageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        runtime = secret_free_validated_data(data)
        try:
            connector = build_connector(data_source, runtime)
            result = connector.read_page(
                schema=data["schema"],
                table=data["table"],
                columns=data.get("columns"),
                limit=data.get("limit", 100),
                offset=data.get("offset", 0),
                cursor_field=data.get("cursor_field"),
                cursor_gt=data.get("cursor_gt"),
            )
            return Response(result)
        except ConnectorError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
