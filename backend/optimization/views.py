from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from execution.models import Execution
from execution.services import create_execution

from .models import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationParameter,
    OptimizationRun,
    OptimizationScenario,
    OptimizationSolutionAsset,
    OptimizationVariable,
    SolverConfig,
)
from .serializers import (
    OptimizationConstraintSerializer,
    OptimizationModelSerializer,
    OptimizationObjectiveSerializer,
    OptimizationParameterSerializer,
    OptimizationRunSerializer,
    OptimizationScenarioSerializer,
    OptimizationSolutionAssetSerializer,
    OptimizationVariableSerializer,
    RunRequestSerializer,
    SolverConfigSerializer,
    can_build,
)
from .tasks import run_optimization_task
from .validation import validate_model_definition


class ModelChildMixin:
    def _scoped(self, queryset):
        return queryset.filter(
            model__workspace__organization__memberships__user=self.request.user,
            model__workspace__organization__memberships__is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        model = serializer.validated_data["model"]
        if not can_build(self.request.user, model.workspace):
            raise PermissionDenied("No tiene permisos sobre este modelo.")
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        if not can_build(self.request.user, obj.model.workspace):
            raise PermissionDenied("No tiene permisos sobre este modelo.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_build(self.request.user, instance.model.workspace):
            raise PermissionDenied("No tiene permisos sobre este modelo.")
        instance.delete()


class OptimizationModelViewSet(viewsets.ModelViewSet):
    serializer_class = OptimizationModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OptimizationModel.objects.filter(
            workspace__organization__memberships__user=self.request.user,
            workspace__organization__memberships__is_active=True,
        ).select_related(
            "workspace",
            "data_asset",
        ).prefetch_related(
            "parameters",
            "variables",
            "constraints",
            "solver_configs",
        ).distinct()
        workspace = self.request.query_params.get("workspace")
        return qs.filter(workspace_id=workspace) if workspace else qs

    @action(detail=True, methods=["get"], url_path="validate")
    def validate_definition(self, request, pk=None):
        return Response(validate_model_definition(self.get_object()))

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        model = self.get_object()
        if not can_build(request.user, model.workspace):
            return Response(status=status.HTTP_403_FORBIDDEN)

        validation = validate_model_definition(model)
        if not validation["valid"]:
            return Response(
                {
                    "detail": "El modelo no está listo para ejecución.",
                    "validation": validation,
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = RunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scenario = serializer.validated_data["scenario"]
        solver_config = serializer.validated_data.get("solver_config")

        if scenario.model_id != model.id:
            return Response(
                {"detail": "El escenario no pertenece al modelo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if solver_config is None:
            solver_config = (
                model.solver_configs.filter(is_default=True).first()
                or model.solver_configs.first()
            )
        if solver_config is None:
            return Response(
                {"detail": "El modelo no tiene SolverConfig."},
                status=status.HTTP_409_CONFLICT,
            )
        if solver_config.model_id != model.id:
            return Response(
                {"detail": "SolverConfig no pertenece al modelo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run = OptimizationRun.objects.create(
            model=model,
            scenario=scenario,
            solver_config=solver_config,
        )
        execution = create_execution(
            workspace=model.workspace,
            object_type=Execution.ObjectType.OPTIMIZATION,
            object_id=model.id,
            queue="optimization",
            requested_by=request.user,
            parameters={
                "optimization_run_id": str(run.id),
                "scenario_id": str(scenario.id),
                "solver_config_id": str(solver_config.id),
            },
        )
        run.execution_id = execution.id
        run.save(update_fields=["execution_id"])

        async_result = run_optimization_task.apply_async(
            args=[str(execution.id), str(run.id)],
            queue="optimization",
        )
        execution.celery_task_id = async_result.id or ""
        execution.save(update_fields=["celery_task_id"])

        return Response(
            {
                "optimization_run_id": str(run.id),
                "execution_id": str(execution.id),
                "solver": solver_config.adapter,
                "status": run.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class OptimizationParameterViewSet(ModelChildMixin, viewsets.ModelViewSet):
    serializer_class = OptimizationParameterSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return self._scoped(
            OptimizationParameter.objects.select_related(
                "model", "source_asset", "source_field"
            )
        )


class OptimizationVariableViewSet(ModelChildMixin, viewsets.ModelViewSet):
    serializer_class = OptimizationVariableSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return self._scoped(
            OptimizationVariable.objects.select_related("model")
        )


class OptimizationObjectiveViewSet(ModelChildMixin, viewsets.ModelViewSet):
    serializer_class = OptimizationObjectiveSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return self._scoped(
            OptimizationObjective.objects.select_related("model")
        )


class OptimizationConstraintViewSet(ModelChildMixin, viewsets.ModelViewSet):
    serializer_class = OptimizationConstraintSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return self._scoped(
            OptimizationConstraint.objects.select_related("model")
        )


class SolverConfigViewSet(ModelChildMixin, viewsets.ModelViewSet):
    serializer_class = SolverConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return self._scoped(
            SolverConfig.objects.select_related("model")
        )

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        if instance.is_default:
            SolverConfig.objects.filter(
                model=instance.model,
                is_default=True,
            ).exclude(id=instance.id).update(is_default=False)


class OptimizationScenarioViewSet(ModelChildMixin, viewsets.ModelViewSet):
    serializer_class = OptimizationScenarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return self._scoped(
            OptimizationScenario.objects.select_related("model")
        )


class OptimizationRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OptimizationRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OptimizationRun.objects.filter(
            model__workspace__organization__memberships__user=self.request.user,
            model__workspace__organization__memberships__is_active=True,
        ).select_related(
            "model",
            "scenario",
            "solver_config",
        ).distinct()
        model_id = self.request.query_params.get("model")
        scenario_id = self.request.query_params.get("scenario")
        run_status = self.request.query_params.get("status")
        if model_id:
            qs = qs.filter(model_id=model_id)
        if scenario_id:
            qs = qs.filter(scenario_id=scenario_id)
        if run_status:
            qs = qs.filter(status=run_status)
        return qs


class OptimizationSolutionAssetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OptimizationSolutionAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OptimizationSolutionAsset.objects.filter(
            run__model__workspace__organization__memberships__user=self.request.user,
            run__model__workspace__organization__memberships__is_active=True,
        ).select_related(
            "run",
            "run__model",
            "data_asset",
        ).distinct()
