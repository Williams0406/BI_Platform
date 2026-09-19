from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetLineageView,
    AssetStateViewSet,
    ChangeEventViewSet,
    DependencyViewSet,
)

router = DefaultRouter()
router.register("edges", DependencyViewSet, basename="dependency")
router.register("states", AssetStateViewSet, basename="asset-state")
router.register("events", ChangeEventViewSet, basename="change-event")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "lineage/<uuid:pk>/",
        AssetLineageView.as_view(),
        name="asset-lineage",
    ),
]
