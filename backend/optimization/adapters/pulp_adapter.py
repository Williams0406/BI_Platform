import time
import pulp
from .base import BaseOptimizationAdapter, SolverResult

class PuLPAdapter(BaseOptimizationAdapter):
    name = "PULP"

    def solve(self, compiled_model, solver_config):
        sense = pulp.LpMaximize if compiled_model["objective"]["sense"] == "MAXIMIZE" else pulp.LpMinimize
        problem = pulp.LpProblem("business_intelligence_optimization", sense)

        variables = {}
        for item in compiled_model["variables"]:
            if item["type"] == "BINARY":
                category = pulp.LpBinary
                lb, ub = 0, 1
            elif item["type"] == "INTEGER":
                category = pulp.LpInteger
                lb, ub = item["lb"], item["ub"]
            else:
                category = pulp.LpContinuous
                lb, ub = item["lb"], item["ub"]
            variables[item["name"]] = pulp.LpVariable(
                item["name"], lowBound=lb, upBound=ub, cat=category
            )

        obj = compiled_model["objective"]["expression"]
        problem += (
            pulp.lpSum(coef * variables[name] for name, coef in obj["terms"])
            + obj["constant"]
        )

        for constraint in compiled_model["constraints"]:
            left = constraint["left"]
            expression = (
                pulp.lpSum(coef * variables[name] for name, coef in left["terms"])
                + left["constant"]
            )
            if constraint["sense"] == "LE":
                problem += expression <= constraint["right"], constraint["name"]
            elif constraint["sense"] == "GE":
                problem += expression >= constraint["right"], constraint["name"]
            else:
                problem += expression == constraint["right"], constraint["name"]

        solver_name = (solver_config.solver_name or "PULP_CBC_CMD").upper()
        if solver_name != "PULP_CBC_CMD":
            raise RuntimeError(
                "El adapter PuLP de Fase 9 soporta PULP_CBC_CMD. "
                "Use Pyomo para otros solvers externos."
            )

        kwargs = {
            "msg": False,
            "timeLimit": solver_config.time_limit_seconds,
        }
        if solver_config.mip_gap is not None:
            kwargs["gapRel"] = solver_config.mip_gap
        if solver_config.threads:
            kwargs["threads"] = solver_config.threads

        solver = pulp.PULP_CBC_CMD(**kwargs)
        started = time.perf_counter()
        problem.solve(solver)
        elapsed = int((time.perf_counter() - started) * 1000)

        raw_status = pulp.LpStatus.get(problem.status, "Undefined")
        status_map = {
            "Optimal": "OPTIMAL",
            "Not Solved": "FAILED",
            "Infeasible": "INFEASIBLE",
            "Unbounded": "UNBOUNDED",
            "Undefined": "FAILED",
        }
        status = status_map.get(raw_status, "FEASIBLE" if raw_status == "Integer Feasible" else "FAILED")

        values = {}
        objective_value = None
        if status in {"OPTIMAL", "FEASIBLE"}:
            values = {
                name: float(var.value()) if var.value() is not None else 0.0
                for name, var in variables.items()
            }
            objective_value = float(pulp.value(problem.objective))

        return SolverResult(
            status=status,
            objective_value=objective_value,
            variable_values=values,
            solve_time_ms=elapsed,
            metadata={
                "adapter": self.name,
                "solver_name": solver_name,
                "pulp_status": raw_status,
            },
        )
