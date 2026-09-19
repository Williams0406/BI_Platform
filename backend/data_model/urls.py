from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .managed_views import ManagedTableCreateView, ManagedTableDeleteView
from .views import CatalogRelationViewSet, CatalogSyncView, CatalogTableViewSet, FieldContentRuleViewSet, PlatformFieldCreateView

router = DefaultRouter()
router.register("tables", CatalogTableViewSet, basename="catalog-table")
router.register("relations", CatalogRelationViewSet, basename="catalog-relation")
router.register("field-content-rules", FieldContentRuleViewSet, basename="field-content-rule")

urlpatterns = [
    path("", include(router.urls)),
    path("sources/<uuid:pk>/sync/", CatalogSyncView.as_view(), name="catalog-sync"),
    path("managed-tables/", ManagedTableCreateView.as_view(), name="managed-table-create"),
    path("managed-tables/<uuid:pk>/", ManagedTableDeleteView.as_view(), name="managed-table-delete"),
    path("platform-fields/", PlatformFieldCreateView.as_view(), name="platform-field-create"),
]
