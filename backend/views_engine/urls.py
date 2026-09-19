from rest_framework.routers import DefaultRouter

from .views import ViewDefinitionViewSet

router = DefaultRouter()
router.register("", ViewDefinitionViewSet, basename="view-definition")

urlpatterns = router.urls
