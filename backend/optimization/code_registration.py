from django.db import transaction
from common.models import ScriptArtifact
from datasources.models import DataAsset
from execution.models import Execution
from execution.services import create_execution
from .models import OptimizationModel, OptimizationParameter, OptimizationVariable, OptimizationObjective, OptimizationConstraint, OptimizationScenario, SolverConfig, OptimizationRun
from .tasks import run_optimization_task
from .validation import validate_model_definition


def _unique_asset_name(workspace, base, exclude_id=None):
    name = base[:180] or "Optimization model"
    i = 2
    qs = DataAsset.objects.filter(workspace=workspace, name=name)
    if exclude_id: qs = qs.exclude(id=exclude_id)
    while qs.exists():
        suffix=f" ({i})"; name=f"{base[:180-len(suffix)]}{suffix}"; i+=1
        qs=DataAsset.objects.filter(workspace=workspace,name=name)
        if exclude_id: qs=qs.exclude(id=exclude_id)
    return name

@transaction.atomic
def register_code_optimization(block, user, spec, variable_name=None):
    variable_name = variable_name or spec.get("name") or "optimization_model"
    prior = block.artifacts.filter(artifact_type=ScriptArtifact.Type.OPTIMIZATION, name=variable_name).first()
    model = OptimizationModel.objects.filter(id=prior.object_id).first() if prior and prior.object_id else None
    # Keep historical runs immutable: re-executing a solved Code model creates a new definition.
    if model is not None and model.runs.exists():
        model = None
    if model is None:
        name = spec.get("name") or variable_name
        existing_names=set(OptimizationModel.objects.filter(workspace=block.workspace).values_list("name",flat=True))
        candidate=name; n=2
        while candidate in existing_names:
            candidate=f"{name} ({n})"; n+=1
        model=OptimizationModel.objects.create(workspace=block.workspace,name=candidate,description=spec.get("description", ""),problem_type=spec.get("problem_type","MILP"),created_by=user)
        asset=DataAsset.objects.create(workspace=block.workspace,data_source=None,name=_unique_asset_name(block.workspace,candidate),asset_type=DataAsset.AssetType.OPTIMIZATION_MODEL,status=DataAsset.Status.ACTIVE,metadata={"optimization_model_id":str(model.id),"problem_type":model.problem_type,"producer":"PYTHON_SCRIPT","script_block_id":str(block.id)},created_by=user)
        model.data_asset=asset; model.save(update_fields=["data_asset","updated_at"])
    else:
        model.description=spec.get("description",""); model.problem_type=spec.get("problem_type","MILP"); model.save(update_fields=["description","problem_type","updated_at"])
        model.parameters.all().delete(); model.variables.all().delete(); model.constraints.all().delete(); model.solver_configs.all().delete(); model.scenarios.all().delete()
        try: model.objective.delete()
        except Exception: pass
    for p in spec.get("parameters",[]): OptimizationParameter.objects.create(model=model,**p)
    for v in spec.get("variables",[]): OptimizationVariable.objects.create(model=model,**v)
    obj=spec.get("objective") or {}; OptimizationObjective.objects.create(model=model,name=obj.get("name","Objective"),sense=obj.get("sense","MINIMIZE"),expression=obj.get("expression",{}))
    for c in spec.get("constraints",[]): OptimizationConstraint.objects.create(model=model,**c)
    s=spec.get("solver") or {}; solver=SolverConfig.objects.create(model=model,name=s.get("name","Default"),adapter=s.get("adapter","ORTOOLS"),solver_name=s.get("solver_name",""),time_limit_seconds=s.get("time_limit_seconds",300),mip_gap=s.get("mip_gap"),threads=s.get("threads"),options=s.get("options") or {},is_default=True)
    sc=spec.get("scenario") or {}; scenario=OptimizationScenario.objects.create(model=model,name=sc.get("name","Base"),description=sc.get("description",""),parameter_values=sc.get("parameter_values") or {},baseline_values=sc.get("baseline_values") or {},created_by=user)
    validation=validate_model_definition(model)
    if not validation["valid"]: raise ValueError("Optimization model is invalid: " + "; ".join(validation["errors"]))
    artifact,_=ScriptArtifact.objects.update_or_create(script_block=block,artifact_type=ScriptArtifact.Type.OPTIMIZATION,name=variable_name,defaults={"object_type":"OPTIMIZATION_MODEL","object_id":str(model.id),"metadata":{"source":"CODE","variable":variable_name,"solve_requested":bool(spec.get("solve_requested"))}})
    result={"model_id":str(model.id),"name":model.name,"artifact_id":str(artifact.id),"status":"READY","run_id":None,"execution_id":None}
    if spec.get("solve_requested"):
        run=OptimizationRun.objects.create(model=model,scenario=scenario,solver_config=solver)
        execution=create_execution(workspace=model.workspace,object_type=Execution.ObjectType.OPTIMIZATION,object_id=model.id,queue="optimization",requested_by=user,parameters={"optimization_run_id":str(run.id),"scenario_id":str(scenario.id),"solver_config_id":str(solver.id),"source":"CODE","script_block_id":str(block.id)})
        run.execution_id=execution.id; run.save(update_fields=["execution_id"])
        def _enqueue():
            async_result=run_optimization_task.apply_async(args=[str(execution.id),str(run.id)],queue="optimization")
            execution.celery_task_id=async_result.id or ""; execution.save(update_fields=["celery_task_id"])
        transaction.on_commit(_enqueue)
        result.update({"status":"QUEUED","run_id":str(run.id),"execution_id":str(execution.id)})
    return result
