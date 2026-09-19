from rest_framework.routers import DefaultRouter

from .views import (
    ChartDefinitionViewSet,
    DashboardDefinitionViewSet,
    DashboardItemViewSet,
    ReportDefinitionViewSet,
)

router = DefaultRouter()
router.register("charts", ChartDefinitionViewSet, basename="chart")
router.register("dashboards", DashboardDefinitionViewSet, basename="dashboard")
router.register("dashboard-items", DashboardItemViewSet, basename="dashboard-item")
router.register("reports", ReportDefinitionViewSet, basename="report")

urlpatterns = router.urls
