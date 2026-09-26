import json
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from datasources.models import DataAsset
from dependencies.models import AssetDependency
from dependencies.services import create_dependency, ensure_asset_state, record_change
from execution.services import mark_running, mark_success, update_progress, emit_event, report_metric, ensure_not_cancelled
from platform_ops.storage import put_bytes

from .adapters.registry import build_adapter
from .baseline import evaluate_baseline, improvement
from .compiler import compile_model
from .models import OptimizationRun, OptimizationSolutionAsset
from .parameter_service import resolve_parameters


@transaction.atomic
def ensure_model_data_asset(model):
    asset = model.data_asset
    if asset is None:
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
            created_by=model.created_by,
        )
        model.data_asset = asset
        model.save(update_fields=["data_asset", "updated_at"])

    for parameter in model.parameters.select_related("source_asset").all():
        if parameter.source_asset_id:
            create_dependency(
                workspace=model.workspace,
                upstream=parameter.source_asset,
                downstream=asset,
                dependency_type=AssetDependency.DependencyType.MODEL_INPUT,
                refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,
                metadata={
                    "relation": "OPTIMIZATION_PARAMETER",
                    "parameter": parameter.name,
                },
            )
    return asset


def persist_solution(run, result, baseline_result):
    payload = {
        "run_id": str(run.id),
        "model_id": str(run.model_id),
        "scenario_id": str(run.scenario_id),
        "solver_config_id": str(run.solver_config_id),
        "status": result.status,
        "objective_value": result.objective_value,
        "best_bound": result.best_bound,
        "gap": result.gap,
        "solve_time_ms": result.solve_time_ms,
        "variable_values": result.variable_values,
        "baseline": baseline_result,
        "solver_metadata": result.metadata,
    }
    artifact_uri = put_bytes(
        f"optimization/{run.model_id}/{run.id}/solution.json",
        json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"),
        "application/json",
    )

    data_asset = DataAsset.objects.create(
        workspace=run.model.workspace,
        data_source=None,
        name=f"{run.model.name} solution {str(run.id)[:8]}",
        asset_type=DataAsset.AssetType.DATASET,
        status=DataAsset.Status.ACTIVE,
        metadata={
            "storage": "JSON_ARTIFACT",
            "artifact_uri": artifact_uri,
            "artifact_path": artifact_uri,
            "optimization_solution": True,
            "optimization_run_id": str(run.id),
        },
        created_by=run.model.created_by,
    )

    solution = OptimizationSolutionAsset.objects.create(
        run=run,
        data_asset=data_asset,
        artifact_path=artifact_uri,
    )

    model_asset = ensure_model_data_asset(run.model)
    create_dependency(
        workspace=run.model.workspace,
        upstream=model_asset,
        downstream=data_asset,
        dependency_type=AssetDependency.DependencyType.DATA,
        refresh_policy=AssetDependency.RefreshPolicy.MANUAL,
        metadata={"relation": "OPTIMIZATION_SOLUTION"},
    )

    for parameter in run.model.parameters.select_related("source_asset").all():
        if parameter.source_asset_id:
            create_dependency(
                workspace=run.model.workspace,
                upstream=parameter.source_asset,
                downstream=data_asset,
                dependency_type=AssetDependency.DependencyType.DATA,
                refresh_policy=AssetDependency.RefreshPolicy.MANUAL,
                metadata={
                    "relation": "OPTIMIZATION_INPUT",
                    "parameter": parameter.name,
                },
            )

    event = record_change(
        data_asset,
        "REFRESH",
        metadata={
            "optimization_run_id": str(run.id),
            "solution_asset_id": str(solution.id),
        },
    )
    return solution, event


def execute_optimization(execution, run):
    model = run.model
    scenario = run.scenario
    solver_config = run.solver_config

    if not model.enabled:
        raise ValueError("El modelo de optimización está deshabilitado.")

    mark_running(execution)
    run.status = OptimizationRun.Status.RUNNING
    run.started_at = timezone.now()
    run.execution_id = execution.id
    run.save(update_fields=["status", "started_at", "execution_id"])

    ensure_not_cancelled(execution)
    update_progress(execution, 10, "Resolviendo parámetros del escenario.")
    parameters, input_versions = resolve_parameters(model, scenario)

    ensure_not_cancelled(execution)
    update_progress(execution, 25, "Compilando modelo matemático.")
    compiled = compile_model(model, parameters)
    emit_event(execution, "OPTIMIZATION_MODEL_COMPILED", {"problem_type": model.problem_type, "parameters": parameters, "objective": getattr(model.objective, "expression", {}), "constraints": [{"name": c.name, "sense": c.sense, "left": c.left_expression, "right": c.right_value} for c in model.constraints.filter(enabled=True)]}, family="OPTIMIZATION")
    baseline_result = evaluate_baseline(
        compiled,
        scenario.baseline_values or {},
    )

    ensure_not_cancelled(execution)
    update_progress(
        execution,
        40,
        f"Ejecutando solver {solver_config.adapter}.",
    )
    adapter = build_adapter(solver_config)
    emit_event(execution, "OPTIMIZATION_SOLVE_STARTED", {"adapter": solver_config.adapter, "solver_name": solver_config.solver_name, "time_limit_seconds": solver_config.time_limit_seconds}, family="OPTIMIZATION")
    ensure_not_cancelled(execution)
    result = adapter.solve(compiled, solver_config)
    ensure_not_cancelled(execution)
    emit_event(execution, "OPTIMIZATION_PROGRESS", {"incumbent": result.objective_value, "best_bound": result.best_bound, "gap": result.gap, "elapsed_seconds": (result.solve_time_ms or 0) / 1000}, family="OPTIMIZATION")
    if result.objective_value is not None: report_metric(execution, "objective", result.objective_value, scope="solution")
    if result.gap is not None: report_metric(execution, "gap", result.gap, scope="solution")
    emit_event(execution, "OPTIMIZATION_SOLUTION_FOUND", {"status": result.status, "objective": result.objective_value, "best_bound": result.best_bound, "gap": result.gap, "values": result.variable_values}, family="OPTIMIZATION")

    finished = timezone.now()
    run.status = result.status
    run.objective_value = result.objective_value
    run.best_bound = result.best_bound
    run.gap = result.gap
    run.solve_time_ms = result.solve_time_ms
    run.variable_values = result.variable_values
    run.baseline_objective_value = baseline_result["objective_value"]
    run.baseline_feasible = baseline_result["feasible"]
    run.input_asset_versions = input_versions
    run.solver_metadata = {
        **result.metadata,
        "resolved_parameters": parameters,
        "baseline_violations": baseline_result["violations"],
    }
    run.finished_at = finished

    absolute, percent = improvement(
        model.objective.sense,
        result.objective_value,
        baseline_result["objective_value"]
        if baseline_result["feasible"] is not False
        else None,
    )
    run.improvement_absolute = absolute
    run.improvement_percent = percent
    run.save()

    if result.status not in {"OPTIMAL", "FEASIBLE"}:
        final_result = {
            "optimization_run_id": str(run.id),
            "status": result.status,
            "objective_value": result.objective_value,
            "solver_metadata": result.metadata,
            "baseline": baseline_result,
        }
        mark_success(execution, final_result)
        return final_result

    update_progress(execution, 80, "Persistiendo solución y lineage.")
    model_asset = ensure_model_data_asset(model)
    state = ensure_asset_state(model_asset)
    state.status = "FRESH"
    state.last_success_at = finished
    state.last_error = ""
    state.save(
        update_fields=[
            "status",
            "last_success_at",
            "last_error",
            "last_changed_at",
        ]
    )

    solution, event = persist_solution(run, result, baseline_result)

    final_result = {
        "optimization_run_id": str(run.id),
        "status": result.status,
        "objective_value": result.objective_value,
        "best_bound": result.best_bound,
        "gap": result.gap,
        "solve_time_ms": result.solve_time_ms,
        "variable_values": result.variable_values,
        "baseline": baseline_result,
        "improvement_absolute": absolute,
        "improvement_percent": percent,
        "solution_asset_id": str(solution.id),
        "data_asset_id": str(solution.data_asset_id),
        "artifact_path": solution.artifact_path,
        "change_event_id": str(event.id),
    }
    mark_success(execution, final_result)
    return final_result
