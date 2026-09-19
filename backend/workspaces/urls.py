from rest_framework.routers import DefaultRouter

from .views import OrganizationViewSet, WorkspaceViewSet

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("", WorkspaceViewSet, basename="workspace")

urlpatterns = router.urls
