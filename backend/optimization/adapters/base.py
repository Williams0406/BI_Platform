from dataclasses import dataclass, field

@dataclass
class SolverResult:
    status: str
    objective_value: float | None = None
    variable_values: dict = field(default_factory=dict)
    best_bound: float | None = None
    gap: float | None = None
    solve_time_ms: int | None = None
    metadata: dict = field(default_factory=dict)

class BaseOptimizationAdapter:
    name = ""
    def solve(self, compiled_model, solver_config):
        raise NotImplementedError
