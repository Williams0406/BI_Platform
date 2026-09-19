from django.contrib import admin

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


class ParameterInline(admin.TabularInline):
    model = OptimizationParameter
    extra = 0


class VariableInline(admin.TabularInline):
    model = OptimizationVariable
    extra = 0


class ConstraintInline(admin.TabularInline):
    model = OptimizationConstraint
    extra = 0


class SolverInline(admin.TabularInline):
    model = SolverConfig
    extra = 0


@admin.register(OptimizationModel)
class OptimizationModelAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "problem_type", "enabled", "updated_at"]
    list_filter = ["problem_type", "enabled"]
    search_fields = ["name"]
    inlines = [ParameterInline, VariableInline, ConstraintInline, SolverInline]


@admin.register(OptimizationObjective)
class OptimizationObjectiveAdmin(admin.ModelAdmin):
    list_display = ["model", "name", "sense"]


@admin.register(OptimizationScenario)
class OptimizationScenarioAdmin(admin.ModelAdmin):
    list_display = ["name", "model", "updated_at"]


@admin.register(OptimizationRun)
class OptimizationRunAdmin(admin.ModelAdmin):
    list_display = [
        "model",
        "scenario",
        "solver_config",
        "status",
        "objective_value",
        "improvement_percent",
        "solve_time_ms",
        "created_at",
    ]
    list_filter = ["status", "solver_config__adapter"]


@admin.register(OptimizationSolutionAsset)
class OptimizationSolutionAssetAdmin(admin.ModelAdmin):
    list_display = ["run", "data_asset", "created_at"]
