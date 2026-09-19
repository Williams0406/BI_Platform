from .base import RuntimeAdapter

class SolverAdapter(RuntimeAdapter):
    family="OPTIMIZATION"
    def progress(self, context, iteration=None, incumbent=None, best_bound=None, gap=None, elapsed_seconds=None, extra=None):
        payload={"iteration":iteration,"incumbent":incumbent,"best_bound":best_bound,"gap":gap,"elapsed_seconds":elapsed_seconds}
        payload.update(extra or {})
        self.event(context,"OPTIMIZATION_PROGRESS",{k:v for k,v in payload.items() if v is not None})
    def solution(self, context, status, objective=None, values=None):
        self.event(context,"OPTIMIZATION_SOLUTION_FOUND",{"status":status,"objective":objective,"values":values or {}})

class ORToolsAdapter(SolverAdapter): key="ortools"; libraries=("ortools",)
class PyomoAdapter(SolverAdapter): key="pyomo"; libraries=("pyomo",)
class PuLPAdapter(SolverAdapter): key="pulp"; libraries=("pulp",)
