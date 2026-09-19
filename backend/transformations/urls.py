from rest_framework.routers import DefaultRouter

from .views import SQLTransformationViewSet

router = DefaultRouter()
router.register("", SQLTransformationViewSet, basename="sql-transformation")

urlpatterns = router.urls
