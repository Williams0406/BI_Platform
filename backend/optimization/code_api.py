"""Small dependency-free optimization DSL exposed inside Code Python blocks."""

class Model:
    def __init__(self, name, problem_type="MILP", description=""):
        self.name = str(name)
        self.problem_type = str(problem_type).upper()
        self.description = str(description or "")
        self._variables = []
        self._parameters = []
        self._constraints = []
        self._objective = None
        self._scenario = {"name": "Base", "parameter_values": {}, "baseline_values": {}}
        self._solver = {"name": "Default", "adapter": "ORTOOLS", "solver_name": "", "time_limit_seconds": 300, "mip_gap": None, "threads": None, "options": {}}
        self._solve_requested = False

    def parameter(self, name, value, value_type=None, description=""):
        if value_type is None:
            value_type = "BOOLEAN" if isinstance(value, bool) else "INTEGER" if isinstance(value, int) else "NUMBER"
        self._parameters.append({"name": str(name), "value_type": str(value_type).upper(), "default_value": value, "description": description})
        return {"parameter": str(name)}

    def variable(self, name, variable_type="CONTINUOUS", lower_bound=0, upper_bound=None, description=""):
        self._variables.append({"name": str(name), "variable_type": str(variable_type).upper(), "lower_bound": lower_bound, "upper_bound": upper_bound, "description": description})
        return str(name)

    @staticmethod
    def expression(terms=None, constant=0):
        terms = terms or {}
        if isinstance(terms, dict):
            terms = [{"variable": str(k), "coefficient": v} for k, v in terms.items()]
        return {"constant": constant, "terms": list(terms)}

    def minimize(self, terms=None, constant=0, name="Objective"):
        self._objective = {"name": name, "sense": "MINIMIZE", "expression": self.expression(terms, constant)}
        return self

    def maximize(self, terms=None, constant=0, name="Objective"):
        self._objective = {"name": name, "sense": "MAXIMIZE", "expression": self.expression(terms, constant)}
        return self

    def constraint(self, name, terms, sense, right, constant=0, description=""):
        aliases = {"<=": "LE", "=": "EQ", "==": "EQ", ">=": "GE", "LE": "LE", "EQ": "EQ", "GE": "GE"}
        normalized = aliases.get(str(sense).upper(), aliases.get(str(sense)))
        if not normalized:
            raise ValueError("Constraint sense must be <=, =, >=, LE, EQ or GE.")
        self._constraints.append({"name": str(name), "left_expression": self.expression(terms, constant), "sense": normalized, "right_value": right, "description": description, "enabled": True})
        return self

    def scenario(self, name="Base", parameters=None, baseline=None, description=""):
        self._scenario = {"name": str(name), "parameter_values": dict(parameters or {}), "baseline_values": dict(baseline or {}), "description": description}
        return self

    def solver(self, adapter="ORTOOLS", name="Default", solver_name="", time_limit_seconds=300, mip_gap=None, threads=None, **options):
        self._solver = {"name": str(name), "adapter": str(adapter).upper(), "solver_name": str(solver_name or ""), "time_limit_seconds": int(time_limit_seconds), "mip_gap": mip_gap, "threads": threads, "options": options}
        return self

    def solve(self, **kwargs):
        if kwargs:
            self.solver(**kwargs)
        self._solve_requested = True
        return self

    @property
    def _bi_optimization_spec(self):
        if not self._objective:
            raise ValueError("Optimization model requires minimize() or maximize().")
        return {"name": self.name, "description": self.description, "problem_type": self.problem_type, "parameters": self._parameters, "variables": self._variables, "objective": self._objective, "constraints": self._constraints, "scenario": self._scenario, "solver": self._solver, "solve_requested": self._solve_requested}

    def __repr__(self):
        return f"OptimizationModel(name={self.name!r}, variables={len(self._variables)}, constraints={len(self._constraints)}, solve_requested={self._solve_requested})"
