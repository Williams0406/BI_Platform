from rest_framework.routers import DefaultRouter
from .views import ExportJobViewSet, ImportJobViewSet, SourceSyncPolicyViewSet

router = DefaultRouter()
router.register("imports", ImportJobViewSet, basename="import-job")
router.register("exports", ExportJobViewSet, basename="export-job")
router.register("sync-policies", SourceSyncPolicyViewSet, basename="source-sync-policy")
urlpatterns = router.urls
