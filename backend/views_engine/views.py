from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from data_records.exceptions import RecordError

from .models import ViewActionRule, ViewDefinition, ViewFieldBinding
from .permissions import can_read_view, can_write_view
from .serializers import (
    ActionRuleCreateSerializer,
    BindingCreateSerializer,
    ViewDefinitionSerializer,
    ViewFieldBindingSerializer,
    ViewInteractionSerializer,
    ViewBuilderSerializer,
    ViewActionRuleSerializer,
)
from .operational_query import build_operational_plan, execute_operational_plan, execute_operational_writeback
from .dataset_adapters import list_operational_datasets
from .services import (
    execute_interaction,
    validate_view_contract,
    view_data,
    view_schema,
)


class ViewDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = ViewDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = (
            ViewDefinition.objects.filter(
                workspace__organization__memberships__user=self.request.user,
                workspace__organization__memberships__is_active=True,
            )
            .select_related("workspace", "workspace__organization", "source_table")
            .prefetch_related("bindings__field", "action_rules")
            .distinct()
            .order_by("name")
        )

        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        view_type = self.request.query_params.get("view_type")
        if view_type:
            queryset = queryset.filter(view_type=view_type)

        return queryset

    def perform_update(self, serializer):
        view = self.get_object()
        if not can_write_view(self.request.user, view):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tiene permisos para editar esta vista.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_write_view(self.request.user, instance):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tiene permisos para eliminar esta vista.")
        instance.delete()

    @action(detail=True, methods=["get"], url_path="schema")
    def schema(self, request, pk=None):
        view = self.get_object()
        if not can_read_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(view_schema(view))

    @action(detail=True, methods=["get"], url_path="data")
    def data(self, request, pk=None):
        view = self.get_object()
        if not can_read_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            return Response(view_data(view, request.query_params))
        except RecordError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"], url_path="operational-datasets")
    def operational_datasets(self, request, pk=None):
        """OQP8: datasets/assets addressable by the shared Execution IR."""
        view = self.get_object()
        if not can_read_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response({"datasets": list_operational_datasets(view.workspace)})

    @action(detail=True, methods=["get", "post"], url_path="operational-query")
    def operational_query(self, request, pk=None):
        view = self.get_object()
        if not can_read_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            if request.method == "GET":
                return Response(build_operational_plan(view))
            return Response(execute_operational_plan(view, request.data, user=request.user))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="operational-writeback")
    def operational_writeback(self, request, pk=None):
        view = self.get_object()
        if not can_write_view(request.user, view):
            return Response({"detail": "No tiene permisos de writeback sobre esta vista."}, status=status.HTTP_403_FORBIDDEN)
        try:
            return Response(execute_operational_writeback(view, request.data, user=request.user))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RecordError as exc:
            from data_records.exceptions import RecordConflictError, RecordNotFoundError
            code = status.HTTP_409_CONFLICT if isinstance(exc, RecordConflictError) else status.HTTP_404_NOT_FOUND if isinstance(exc, RecordNotFoundError) else status.HTTP_400_BAD_REQUEST
            return Response({"detail": str(exc)}, status=code)

    @action(detail=True, methods=["get"], url_path="validate")
    def validate_contract(self, request, pk=None):
        view = self.get_object()
        return Response(validate_view_contract(view))

    @action(detail=True, methods=["post"], url_path="bindings")
    def create_binding(self, request, pk=None):
        view = self.get_object()
        if not can_write_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = BindingCreateSerializer(
            data=request.data,
            context={"request": request, "view": view},
        )
        serializer.is_valid(raise_exception=True)
        binding = serializer.save(view=view)

        return Response(
            ViewFieldBindingSerializer(binding).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"bindings/(?P<binding_id>[0-9a-f-]+)",
    )
    def delete_binding(self, request, pk=None, binding_id=None):
        view = self.get_object()
        if not can_write_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)

        deleted, _ = ViewFieldBinding.objects.filter(
            id=binding_id,
            view=view,
        ).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="actions")
    def create_action_rule(self, request, pk=None):
        view = self.get_object()
        if not can_write_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ActionRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = serializer.save(view=view)
        return Response(
            ViewActionRuleSerializer(rule).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["put"], url_path="builder")
    def save_builder(self, request, pk=None):
        view = self.get_object()
        if not can_write_view(request.user, view):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ViewBuilderSerializer(data=request.data, context={"request": request, "view": view})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        view.config = data["config"]
        if "name" in data:
            view.name = data["name"]
        if "view_type" in data:
            view.view_type = data["view_type"]
        view.save(update_fields=["config", "name", "view_type", "updated_at"])

        ViewFieldBinding.objects.filter(view=view).delete()
        ViewFieldBinding.objects.bulk_create([
            ViewFieldBinding(view=view, **binding) for binding in data.get("bindings", [])
        ])
        view.refresh_from_db()
        return Response(view_schema(view))

    @action(detail=True, methods=["post"], url_path="interact")
    def interact(self, request, pk=None):
        view = self.get_object()
        if not can_write_view(request.user, view):
            return Response(
                {"detail": "No tiene permisos de writeback sobre esta vista."},
                status=status.HTTP_403_FORBIDDEN,
            )

        contract = validate_view_contract(view)
        if not contract["valid"]:
            return Response(
                {
                    "detail": "La vista todavía no cumple su contrato de bindings.",
                    "contract": contract,
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ViewInteractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            row = execute_interaction(
                view=view,
                record_key=data["record_key"],
                expected_version=data["expected_version"],
                action=data["action"],
                values=data["values"],
            )
            return Response(row)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RecordError as exc:
            # Preserve concurrency semantics of Phase 4.
            from data_records.exceptions import (
                RecordConflictError,
                RecordNotFoundError,
            )
            if isinstance(exc, RecordConflictError):
                code = status.HTTP_409_CONFLICT
            elif isinstance(exc, RecordNotFoundError):
                code = status.HTTP_404_NOT_FOUND
            else:
                code = status.HTTP_400_BAD_REQUEST

            return Response({"detail": str(exc)}, status=code)
