from rest_framework import serializers

from datasources.models import DataAsset

from workspaces.models import Membership

from .expression import OptimizationExpressionError, validate_expression
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


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def can_build(user, workspace):
    return Membership.objects.filter(
        organization=workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()


class OptimizationParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationParameter
        fields = [
            "id",
            "model",
            "name",
            "value_type",
            "default_value",
            "source_asset",
            "source_field",
            "source_column",
            "source_aggregation",
            "description",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        model = attrs.get("model", getattr(self.instance, "model", None))
        asset = attrs.get("source_asset", getattr(self.instance, "source_asset", None))
        field = attrs.get("source_field", getattr(self.instance, "source_field", None))
        if asset and model and asset.workspace_id != model.workspace_id:
            raise serializers.ValidationError(
                "El DataAsset del parámetro debe pertenecer al mismo workspace."
            )
        if field and asset:
            try:
                table = asset.table_definition
            except Exception:
                table = None
            if table and field.table_asset_id != table.id:
                raise serializers.ValidationError(
                    "source_field no pertenece al source_asset."
                )
        if asset and not field and not attrs.get(
            "source_column",
            getattr(self.instance, "source_column", ""),
        ):
            raise serializers.ValidationError(
                "Un source_asset requiere source_field o source_column."
            )
        return attrs


class OptimizationVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationVariable
        fields = [
            "id",
            "model",
            "name",
            "variable_type",
            "lower_bound",
            "upper_bound",
            "description",
        ]
        read_only_fields = ["id"]


class OptimizationObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationObjective
        fields = ["id", "model", "name", "sense", "expression"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        model = attrs.get("model", getattr(self.instance, "model", None))
        expression = attrs.get("expression", getattr(self.instance, "expression", {}))
        if model:
            try:
                validate_expression(
                    expression,
                    set(model.variables.values_list("name", flat=True)),
                    set(model.parameters.values_list("name", flat=True)),
                )
            except OptimizationExpressionError as exc:
                raise serializers.ValidationError({"expression": str(exc)})
        return attrs


class OptimizationConstraintSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationConstraint
        fields = [
            "id",
            "model",
            "name",
            "left_expression",
            "sense",
            "right_value",
            "enabled",
            "description",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        model = attrs.get("model", getattr(self.instance, "model", None))
        expression = attrs.get(
            "left_expression",
            getattr(self.instance, "left_expression", {}),
        )
        right_value = attrs.get(
            "right_value",
            getattr(self.instance, "right_value", None),
        )
        if model:
            variable_names = set(model.variables.values_list("name", flat=True))
            parameter_names = set(model.parameters.values_list("name", flat=True))
            try:
                validate_expression(expression, variable_names, parameter_names)
                if isinstance(right_value, dict):
                    if set(right_value) != {"parameter"} or right_value["parameter"] not in parameter_names:
                        raise OptimizationExpressionError(
                            "right_value parametrizado inválido."
                        )
                elif not isinstance(right_value, (int, float)):
                    raise OptimizationExpressionError(
                        "right_value debe ser número o parámetro."
                    )
            except OptimizationExpressionError as exc:
                raise serializers.ValidationError(str(exc))
        return attrs


class SolverConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolverConfig
        fields = [
            "id",
            "model",
            "name",
            "adapter",
            "solver_name",
            "time_limit_seconds",
            "mip_gap",
            "threads",
            "options",
            "is_default",
        ]
        read_only_fields = ["id"]

    def validate_mip_gap(self, value):
        if value is not None and not 0 <= value <= 1:
            raise serializers.ValidationError("mip_gap debe estar entre 0 y 1.")
        return value


class OptimizationScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationScenario
        fields = [
            "id",
            "model",
            "name",
            "description",
            "parameter_values",
            "baseline_values",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        return OptimizationScenario.objects.create(
            created_by=self.context["request"].user,
            **validated_data,
        )


class OptimizationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationRun
        fields = [
            "id",
            "model",
            "scenario",
            "solver_config",
            "execution_id",
            "status",
            "objective_value",
            "best_bound",
            "gap",
            "solve_time_ms",
            "variable_values",
            "baseline_objective_value",
            "baseline_feasible",
            "improvement_absolute",
            "improvement_percent",
            "input_asset_versions",
            "solver_metadata",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        ]


class OptimizationSolutionAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationSolutionAsset
        fields = ["id", "run", "data_asset", "artifact_path", "created_at"]


class OptimizationModelSerializer(serializers.ModelSerializer):
    parameters = OptimizationParameterSerializer(many=True, read_only=True)
    variables = OptimizationVariableSerializer(many=True, read_only=True)
    constraints = OptimizationConstraintSerializer(many=True, read_only=True)
    objective = OptimizationObjectiveSerializer(read_only=True)
    solver_configs = SolverConfigSerializer(many=True, read_only=True)

    class Meta:
        model = OptimizationModel
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "problem_type",
            "enabled",
            "data_asset",
            "parameters",
            "variables",
            "objective",
            "constraints",
            "solver_configs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "data_asset", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        if not can_build(request.user, validated_data["workspace"]):
            raise serializers.ValidationError(
                "No tiene permisos para crear modelos de optimización."
            )
        model = OptimizationModel.objects.create(
            created_by=request.user,
            **validated_data,
        )
        asset = DataAsset.objects.create(
            workspace=model.workspace,
            data_source=None,
            name=model.name,
            asset_type=DataAsset.AssetType.OPTIMIZATION_MODEL,
            status=DataAsset.Status.ACTIVE,
            metadata={
                "optimization_model_id": str(model.id),
                "problem_type": model.problem_type,
            },
            created_by=request.user,
        )
        model.data_asset = asset
        model.save(update_fields=["data_asset", "updated_at"])
        return model


class RunRequestSerializer(serializers.Serializer):
    scenario = serializers.PrimaryKeyRelatedField(
        queryset=OptimizationScenario.objects.all()
    )
    solver_config = serializers.PrimaryKeyRelatedField(
        queryset=SolverConfig.objects.all(),
        required=False,
        allow_null=True,
    )
