from optimization.models import SolverConfig
from .ortools_adapter import ORToolsAdapter
from .pulp_adapter import PuLPAdapter
from .pyomo_adapter import PyomoAdapter

ADAPTERS = {
    SolverConfig.Adapter.ORTOOLS: ORToolsAdapter,
    SolverConfig.Adapter.PULP: PuLPAdapter,
    SolverConfig.Adapter.PYOMO: PyomoAdapter,
}

def build_adapter(solver_config):
    adapter_cls = ADAPTERS.get(solver_config.adapter)
    if not adapter_cls:
        raise RuntimeError(f"Adapter no soportado: {solver_config.adapter}")
    return adapter_cls()
