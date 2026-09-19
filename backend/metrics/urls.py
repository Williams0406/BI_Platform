from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MetricDefinitionViewSet,
    SemanticDimensionViewSet,
    SemanticModelViewSet,
)

router = DefaultRouter()
router.register("semantic-models", SemanticModelViewSet, basename="semantic-model")
router.register("dimensions", SemanticDimensionViewSet, basename="semantic-dimension")
router.register("", MetricDefinitionViewSet, basename="metric")

urlpatterns = [
    path("", include(router.urls)),
]
