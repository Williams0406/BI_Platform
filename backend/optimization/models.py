import uuid

from django.conf import settings
from django.db import models

from data_model.models import FieldAsset
from datasources.models import DataAsset
from workspaces.models import Workspace


class OptimizationModel(models.Model):
    class ProblemType(models.TextChoices):
        LP = "LP", "Linear Programming"
        MILP = "MILP", "Mixed Integer Linear Programming"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="optimization_models",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    problem_type = models.CharField(
        max_length=20,
        choices=ProblemType.choices,
        default=ProblemType.MILP,
    )
    enabled = models.BooleanField(default=True)
    data_asset = models.OneToOneField(
        DataAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="optimization_model_definition",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="optimization_models_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_optimization_model_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.name


class OptimizationParameter(models.Model):
    class ValueType(models.TextChoices):
        NUMBER = "NUMBER", "Número"
        INTEGER = "INTEGER", "Entero"
        BOOLEAN = "BOOLEAN", "Booleano"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="parameters",
    )
    name = models.CharField(max_length=120)
    value_type = models.CharField(
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.NUMBER,
    )
    default_value = models.JSONField(null=True, blank=True)
    source_asset = models.ForeignKey(
        DataAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="optimization_parameters",
    )
    source_field = models.ForeignKey(
        FieldAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="optimization_parameters",
    )
    source_column = models.CharField(
        max_length=180,
        blank=True,
        help_text="Column name for CSV/artifact Data Assets.",
    )
    source_aggregation = models.CharField(
        max_length=30,
        blank=True,
        help_text="SUM/AVG/MIN/MAX/COUNT for scalar binding.",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "name"],
                name="unique_optimization_parameter_name",
            )
        ]


class OptimizationVariable(models.Model):
    class VariableType(models.TextChoices):
        CONTINUOUS = "CONTINUOUS", "Continua"
        INTEGER = "INTEGER", "Entera"
        BINARY = "BINARY", "Binaria"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="variables",
    )
    name = models.CharField(max_length=120)
    variable_type = models.CharField(
        max_length=20,
        choices=VariableType.choices,
        default=VariableType.CONTINUOUS,
    )
    lower_bound = models.JSONField(default=int)
    upper_bound = models.JSONField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "name"],
                name="unique_optimization_variable_name",
            )
        ]


class OptimizationObjective(models.Model):
    class Sense(models.TextChoices):
        MINIMIZE = "MINIMIZE", "Minimizar"
        MAXIMIZE = "MAXIMIZE", "Maximizar"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.OneToOneField(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="objective",
    )
    name = models.CharField(max_length=180, default="Objective")
    sense = models.CharField(
        max_length=20,
        choices=Sense.choices,
        default=Sense.MINIMIZE,
    )
    expression = models.JSONField(
        default=dict,
        help_text='{"constant":0,"terms":[{"variable":"x","coefficient":10}]}',
    )


class OptimizationConstraint(models.Model):
    class Sense(models.TextChoices):
        LE = "LE", "<="
        EQ = "EQ", "="
        GE = "GE", ">="

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="constraints",
    )
    name = models.CharField(max_length=180)
    left_expression = models.JSONField(default=dict)
    sense = models.CharField(max_length=10, choices=Sense.choices)
    right_value = models.JSONField(help_text="Scalar or {'parameter':'capacity'}.")
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "name"],
                name="unique_optimization_constraint_name",
            )
        ]


class SolverConfig(models.Model):
    class Adapter(models.TextChoices):
        ORTOOLS = "ORTOOLS", "OR-Tools"
        PULP = "PULP", "PuLP"
        PYOMO = "PYOMO", "Pyomo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="solver_configs",
    )
    name = models.CharField(max_length=120)
    adapter = models.CharField(max_length=20, choices=Adapter.choices)
    solver_name = models.CharField(
        max_length=80,
        blank=True,
        help_text="For Pyomo, e.g. highs/glpk/cbc. Optional for other adapters.",
    )
    time_limit_seconds = models.PositiveIntegerField(default=300)
    mip_gap = models.FloatField(null=True, blank=True)
    threads = models.PositiveIntegerField(null=True, blank=True)
    options = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "name"],
                name="unique_solver_config_name_per_model",
            )
        ]


class OptimizationScenario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="scenarios",
    )
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    parameter_values = models.JSONField(default=dict, blank=True)
    baseline_values = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"x": 10, "y": 2}',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="optimization_scenarios_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "name"],
                name="unique_optimization_scenario_name",
            )
        ]


class OptimizationRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "En cola"
        RUNNING = "RUNNING", "Ejecutando"
        OPTIMAL = "OPTIMAL", "Óptima"
        FEASIBLE = "FEASIBLE", "Factible"
        INFEASIBLE = "INFEASIBLE", "Infactible"
        UNBOUNDED = "UNBOUNDED", "No acotada"
        FAILED = "FAILED", "Fallida"
        CANCELLED = "CANCELLED", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        OptimizationModel,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    scenario = models.ForeignKey(
        OptimizationScenario,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    solver_config = models.ForeignKey(
        SolverConfig,
        on_delete=models.PROTECT,
        related_name="runs",
    )
    execution_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    objective_value = models.FloatField(null=True, blank=True)
    best_bound = models.FloatField(null=True, blank=True)
    gap = models.FloatField(null=True, blank=True)
    solve_time_ms = models.PositiveBigIntegerField(null=True, blank=True)
    variable_values = models.JSONField(default=dict, blank=True)
    baseline_objective_value = models.FloatField(null=True, blank=True)
    baseline_feasible = models.BooleanField(null=True, blank=True)
    improvement_absolute = models.FloatField(null=True, blank=True)
    improvement_percent = models.FloatField(null=True, blank=True)
    input_asset_versions = models.JSONField(default=dict, blank=True)
    solver_metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class OptimizationSolutionAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.OneToOneField(
        OptimizationRun,
        on_delete=models.CASCADE,
        related_name="solution_asset",
    )
    data_asset = models.OneToOneField(
        DataAsset,
        on_delete=models.CASCADE,
        related_name="optimization_solution",
    )
    artifact_path = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
