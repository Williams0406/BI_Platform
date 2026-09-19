from .base import RuntimeAdapter, AdapterRegistry
from .ml import SklearnAdapter, TensorFlowAdapter, PyTorchAdapter
from .optimization import ORToolsAdapter, PyomoAdapter, PuLPAdapter

DEFAULT_ADAPTERS = AdapterRegistry([
    SklearnAdapter(), TensorFlowAdapter(), PyTorchAdapter(),
    ORToolsAdapter(), PyomoAdapter(), PuLPAdapter(),
])
