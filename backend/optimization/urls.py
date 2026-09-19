from rest_framework.routers import DefaultRouter

from .views import (
    OptimizationConstraintViewSet,
    OptimizationModelViewSet,
    OptimizationObjectiveViewSet,
    OptimizationParameterViewSet,
    OptimizationRunViewSet,
    OptimizationScenarioViewSet,
    OptimizationSolutionAssetViewSet,
    OptimizationVariableViewSet,
    SolverConfigViewSet,
)

router = DefaultRouter()
router.register("models", OptimizationModelViewSet, basename="optimization-model")
router.register("parameters", OptimizationParameterViewSet, basename="optimization-parameter")
router.register("variables", OptimizationVariableViewSet, basename="optimization-variable")
router.register("objectives", OptimizationObjectiveViewSet, basename="optimization-objective")
router.register("constraints", OptimizationConstraintViewSet, basename="optimization-constraint")
router.register("solver-configs", SolverConfigViewSet, basename="solver-config")
router.register("scenarios", OptimizationScenarioViewSet, basename="optimization-scenario")
router.register("runs", OptimizationRunViewSet, basename="optimization-run")
router.register("solutions", OptimizationSolutionAssetViewSet, basename="optimization-solution")

urlpatterns = router.urls
