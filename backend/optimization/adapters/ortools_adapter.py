import time
from ortools.linear_solver import pywraplp
from .base import BaseOptimizationAdapter, SolverResult

class ORToolsAdapter(BaseOptimizationAdapter):
    name = "ORTOOLS"

    def solve(self, compiled_model, solver_config):
        solver_name = solver_config.solver_name or "SCIP"
        solver = pywraplp.Solver.CreateSolver(solver_name)
        if solver is None:
            raise RuntimeError(f"OR-Tools no pudo crear solver '{solver_name}'.")

        if solver_config.time_limit_seconds:
            solver.SetTimeLimit(int(solver_config.time_limit_seconds * 1000))
        if solver_config.threads:
            try:
                solver.SetNumThreads(int(solver_config.threads))
            except Exception:
                pass

        variables = {}
        infinity = solver.infinity()
        for item in compiled_model["variables"]:
            lb = item["lb"] if item["lb"] is not None else -infinity
            ub = item["ub"] if item["ub"] is not None else infinity
            if item["type"] == "BINARY":
                var = solver.IntVar(0, 1, item["name"])
            elif item["type"] == "INTEGER":
                var = solver.IntVar(lb, ub, item["name"])
            else:
                var = solver.NumVar(lb, ub, item["name"])
            variables[item["name"]] = var

        for constraint in compiled_model["constraints"]:
            left = constraint["left"]
            rhs = float(constraint["right"] - left["constant"])
            if constraint["sense"] == "LE":
                row = solver.RowConstraint(-infinity, rhs, constraint["name"])
            elif constraint["sense"] == "GE":
                row = solver.RowConstraint(rhs, infinity, constraint["name"])
            else:
                row = solver.RowConstraint(rhs, rhs, constraint["name"])
            for var_name, coefficient in left["terms"]:
                row.SetCoefficient(variables[var_name], coefficient)

        objective_data = compiled_model["objective"]["expression"]
        objective = solver.Objective()
        for var_name, coefficient in objective_data["terms"]:
            objective.SetCoefficient(variables[var_name], coefficient)
        objective.SetOffset(objective_data["constant"])
        if compiled_model["objective"]["sense"] == "MAXIMIZE":
            objective.SetMaximization()
        else:
            objective.SetMinimization()

        started = time.perf_counter()
        status_code = solver.Solve()
        elapsed = int((time.perf_counter() - started) * 1000)

        status_map = {
            pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE",
            pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
            pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
            pywraplp.Solver.ABNORMAL: "FAILED",
            pywraplp.Solver.NOT_SOLVED: "FAILED",
        }
        status = status_map.get(status_code, "FAILED")

        values = {}
        objective_value = None
        best_bound = None
        gap = None
        if status in {"OPTIMAL", "FEASIBLE"}:
            values = {name: float(var.solution_value()) for name, var in variables.items()}
            objective_value = float(objective.Value())
            try:
                best_bound = float(objective.BestBound())
                if objective_value and objective_value != 0:
                    gap = abs(objective_value - best_bound) / abs(objective_value)
            except Exception:
                pass

        return SolverResult(
            status=status,
            objective_value=objective_value,
            variable_values=values,
            best_bound=best_bound,
            gap=gap,
            solve_time_ms=elapsed,
            metadata={
                "adapter": self.name,
                "solver_name": solver_name,
                "wall_time_ms": solver.wall_time(),
                "iterations": solver.iterations(),
                "nodes": solver.nodes(),
            },
        )
