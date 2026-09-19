import time
import pyomo.environ as pyo
from .base import BaseOptimizationAdapter, SolverResult

class PyomoAdapter(BaseOptimizationAdapter):
    name = "PYOMO"

    def solve(self, compiled_model, solver_config):
        solver_name = solver_config.solver_name or "highs"
        model = pyo.ConcreteModel()

        variable_names = [item["name"] for item in compiled_model["variables"]]
        model.V = pyo.Set(initialize=variable_names)

        variable_specs = {item["name"]: item for item in compiled_model["variables"]}

        def bounds_rule(m, name):
            item = variable_specs[name]
            return (item["lb"], item["ub"])

        def domain_rule(m, name):
            item = variable_specs[name]
            if item["type"] == "BINARY":
                return pyo.Binary
            if item["type"] == "INTEGER":
                return pyo.Integers
            return pyo.Reals

        model.x = pyo.Var(model.V, bounds=bounds_rule, domain=domain_rule)

        obj = compiled_model["objective"]["expression"]
        objective_expr = obj["constant"] + sum(
            coef * model.x[name] for name, coef in obj["terms"]
        )
        sense = pyo.maximize if compiled_model["objective"]["sense"] == "MAXIMIZE" else pyo.minimize
        model.objective = pyo.Objective(expr=objective_expr, sense=sense)

        model.constraints = pyo.ConstraintList()
        for item in compiled_model["constraints"]:
            left = item["left"]["constant"] + sum(
                coef * model.x[name] for name, coef in item["left"]["terms"]
            )
            if item["sense"] == "LE":
                model.constraints.add(left <= item["right"])
            elif item["sense"] == "GE":
                model.constraints.add(left >= item["right"])
            else:
                model.constraints.add(left == item["right"])

        solver = pyo.SolverFactory(solver_name)
        if solver is None or not solver.available(False):
            raise RuntimeError(
                f"Pyomo está instalado, pero el solver externo '{solver_name}' no está disponible."
            )

        options = dict(solver_config.options or {})
        if solver_config.time_limit_seconds:
            if solver_name.lower() in {"highs", "appsi_highs"}:
                options.setdefault("time_limit", solver_config.time_limit_seconds)
            elif solver_name.lower() in {"cbc"}:
                options.setdefault("seconds", solver_config.time_limit_seconds)
            elif solver_name.lower() in {"glpk"}:
                options.setdefault("tmlim", solver_config.time_limit_seconds)
        if solver_config.mip_gap is not None:
            if solver_name.lower() in {"highs", "appsi_highs"}:
                options.setdefault("mip_rel_gap", solver_config.mip_gap)
            elif solver_name.lower() == "cbc":
                options.setdefault("ratio", solver_config.mip_gap)

        started = time.perf_counter()
        result = solver.solve(model, tee=False, options=options)
        elapsed = int((time.perf_counter() - started) * 1000)

        termination = str(result.solver.termination_condition).lower()
        if "optimal" in termination:
            status = "OPTIMAL"
        elif "feasible" in termination:
            status = "FEASIBLE"
        elif "infeasible" in termination:
            status = "INFEASIBLE"
        elif "unbounded" in termination:
            status = "UNBOUNDED"
        else:
            status = "FAILED"

        values = {}
        objective_value = None
        if status in {"OPTIMAL", "FEASIBLE"}:
            values = {name: float(pyo.value(model.x[name])) for name in variable_names}
            objective_value = float(pyo.value(model.objective))

        return SolverResult(
            status=status,
            objective_value=objective_value,
            variable_values=values,
            solve_time_ms=elapsed,
            metadata={
                "adapter": self.name,
                "solver_name": solver_name,
                "termination_condition": str(result.solver.termination_condition),
                "solver_status": str(result.solver.status),
            },
        )
