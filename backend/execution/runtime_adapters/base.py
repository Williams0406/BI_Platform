from dataclasses import dataclass
from execution.services import emit_event, report_metric

@dataclass
class RuntimeContext:
    execution: object

class RuntimeAdapter:
    key = "base"
    family = "EXECUTION"
    libraries = ()
    def detect(self, imported_modules):
        return any(x == lib or x.startswith(f"{lib}.") for x in imported_modules for lib in self.libraries)
    def event(self, context, event_type, payload=None):
        return emit_event(context.execution, event_type, payload or {}, family=self.family)
    def metric(self, context, name, value, step=None, scope="run"):
        return report_metric(context.execution, name, value, step=step, scope=scope)
    def instrument(self, context, namespace):
        return namespace
    def collect_artifacts(self, context, namespace):
        return []

class AdapterRegistry:
    def __init__(self, adapters=None): self.adapters=list(adapters or [])
    def matching(self, imported_modules): return [a for a in self.adapters if a.detect(imported_modules)]
