from rest_framework.routers import DefaultRouter

from .views import ExecutionViewSet

router = DefaultRouter()
router.register("", ExecutionViewSet, basename="execution")

urlpatterns = router.urls
