from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from connectors.exceptions import ConnectorError
from connectors.permissions import user_can_manage_datasource
from connectors.serializers import CatalogRequestSerializer
from connectors.views import get_accessible_source, secret_free_validated_data

from .models import FieldContentRule, RelationAsset, TableAsset
from .platform_field_serializers import PlatformFieldCreateSerializer
from .platform_field_services import create_platform_field
from .serializers import FieldAssetSerializer, FieldContentRuleSerializer, RelationAssetSerializer, TableAssetSerializer
from .services import sync_catalog


class CatalogTableViewSet(viewsets.ModelViewSet):
    serializer_class = TableAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            TableAsset.objects.filter(
                data_source__workspace__organization__memberships__user=self.request.user,
                data_source__workspace__organization__memberships__is_active=True,
            )
            .select_related("data_asset", "data_source")
            .prefetch_related("fields", "fields__content_rule")
            .distinct()
        )
        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            queryset = queryset.filter(data_source__workspace_id=workspace_id)
        source_id = self.request.query_params.get("data_source")
        if source_id:
            queryset = queryset.filter(data_source_id=source_id)
        schema = self.request.query_params.get("schema")
        if schema:
            queryset = queryset.filter(schema_name=schema)
        return queryset

    def update(self, request, *args, **kwargs):
        table = self.get_object()
        if not user_can_manage_datasource(request.user, table.data_source):
            raise PermissionDenied("No tiene permisos para renombrar esta tabla.")
        requested = request.data.get("technical_name")
        if requested is None:
            return Response({"detail": "technical_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        from .table_rename import rename_table
        try:
            table = rename_table(table, requested)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(table).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        table = self.get_object()
        # Code-generated datasets are platform-owned derived artifacts. Their X
        # action removes the generated table and its derived Data Science tree
        # (dataset/model/runs/report) without requiring a DDL grant.
        from common.generated_outputs import (
            GeneratedOutputInUseError,
            delete_script_generated_table,
            is_script_generated_table,
        )
        if is_script_generated_table(table):
            try:
                delete_script_generated_table(table)
            except GeneratedOutputInUseError as exc:
                return Response(
                    {
                        "detail": str(exc),
                        "code": "GENERATED_DATASET_IN_USE",
                        "dependencies": exc.dependencies,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        if table.data_source.mode != "MANAGED":
            return Response({"detail": "Only Platform tables can be physically deleted from Data."}, status=status.HTTP_400_BAD_REQUEST)
        from .managed_services import delete_managed_table
        from governance.services import audit, GovernanceError, has_resource_permission, mark_destructive_executed, require_approved_destructive_change
        ddl_allowed = has_resource_permission(
            request.user, table.data_source.workspace, "TableAsset", "DDL", table.id
        ) is True
        if not ddl_allowed and not user_can_manage_datasource(request.user, table.data_source):
            raise PermissionDenied("No tiene permisos DDL para eliminar esta tabla.")
        try:
            if ddl_allowed:
                # An explicit table/workspace DDL grant authorizes schema destruction directly.
                workspace = table.data_source.workspace
                resource_id = table.id
                delete_managed_table(table)
                audit(workspace, "DDL_DELETE_TABLE", "TableAsset", resource_id, request.user)
            else:
                approval = require_approved_destructive_change(table.data_source.workspace, "DELETE_MANAGED_TABLE", "TableAsset", table.id)
                delete_managed_table(table)
                mark_destructive_executed(approval, request.user)
        except GovernanceError as exc:
            return Response({"detail": str(exc), "requires_approval": True}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CatalogRelationViewSet(viewsets.ModelViewSet):
    serializer_class = RelationAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            RelationAsset.objects.filter(
                data_source__workspace__organization__memberships__user=self.request.user,
                data_source__workspace__organization__memberships__is_active=True,
            )
            .select_related("data_source", "source_table", "target_table")
            .distinct()
        )
        source_id = self.request.query_params.get("data_source")
        if source_id:
            queryset = queryset.filter(data_source_id=source_id)
        return queryset

    def perform_create(self, serializer):
        source_table = serializer.validated_data["source_table"]
        target_table = serializer.validated_data["target_table"]
        if not user_can_manage_datasource(self.request.user, source_table.data_source):
            raise PermissionDenied("No tiene permisos para crear relaciones desde esta fuente.")
        # Cross-source relations are logical model relations; no DDL is sent to either source.
        if source_table.data_source.workspace_id != target_table.data_source.workspace_id:
            raise PermissionDenied("Las tablas deben pertenecer al mismo workspace.")
        serializer.save(data_source=source_table.data_source)

    def perform_destroy(self, instance):
        if not user_can_manage_datasource(self.request.user, instance.data_source):
            raise PermissionDenied("No tiene permisos para eliminar relaciones en esta fuente.")
        instance.delete()


class FieldContentRuleViewSet(viewsets.ModelViewSet):
    serializer_class = FieldContentRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = FieldContentRule.objects.filter(
            field__table_asset__data_source__workspace__organization__memberships__user=self.request.user,
            field__table_asset__data_source__workspace__organization__memberships__is_active=True,
        ).select_related("field", "field__table_asset", "field__table_asset__data_source").distinct()
        table_id = self.request.query_params.get("table")
        if table_id:
            qs = qs.filter(field__table_asset_id=table_id)
        return qs

    def perform_create(self, serializer):
        field = serializer.validated_data["field"]
        if not user_can_manage_datasource(self.request.user, field.table_asset.data_source):
            raise PermissionDenied("No tiene permisos para configurar este campo.")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        field = serializer.instance.field
        if not user_can_manage_datasource(self.request.user, field.table_asset.data_source):
            raise PermissionDenied("No tiene permisos para configurar este campo.")
        serializer.save()


class PlatformFieldCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PlatformFieldCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        table = serializer.validated_data["table"]
        if not user_can_manage_datasource(request.user, table.data_source):
            return Response({"detail": "No tiene permisos para agregar campos de plataforma."}, status=status.HTTP_403_FORBIDDEN)
        definition = dict(serializer.validated_data)
        definition.pop("table", None)
        field = create_platform_field(table=table, definition=definition)
        return Response(FieldAssetSerializer(field).data, status=status.HTTP_201_CREATED)


class CatalogSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        data_source = get_accessible_source(request.user, pk)
        if not data_source:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not user_can_manage_datasource(request.user, data_source):
            return Response({"detail": "No tiene permisos para sincronizar esta fuente."}, status=status.HTTP_403_FORBIDDEN)
        serializer = CatalogRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        runtime = secret_free_validated_data(data)
        try:
            result = sync_catalog(data_source=data_source, runtime_credentials=runtime, schemas=data.get("schemas"), include_views=data.get("include_views", True), created_by=request.user)
        except ConnectorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"data_source": str(data_source.id), "result": result.to_dict()})
