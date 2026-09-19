from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentClaimJobView,
    AgentCompleteJobView,
    AgentEnrollView,
    AgentHeartbeatView,
    AgentRotateTokenView,
    GatewayBindingViewSet,
    GatewayJobViewSet,
    GatewayRegistrationViewSet,
    GatewayImportRequestViewSet,
)

router = DefaultRouter()
router.register("registrations", GatewayRegistrationViewSet, basename="gateway")
router.register("bindings", GatewayBindingViewSet, basename="gateway-binding")
router.register("jobs", GatewayJobViewSet, basename="gateway-job")
router.register("imports", GatewayImportRequestViewSet, basename="gateway-import")

urlpatterns = [
    path("", include(router.urls)),
    path("agent/enroll/", AgentEnrollView.as_view(), name="gateway-agent-enroll"),
    path("agent/heartbeat/", AgentHeartbeatView.as_view(), name="gateway-agent-heartbeat"),
    path("agent/jobs/claim/", AgentClaimJobView.as_view(), name="gateway-agent-claim"),
    path("agent/jobs/<uuid:job_id>/complete/", AgentCompleteJobView.as_view(), name="gateway-agent-complete"),
    path("agent/token/rotate/", AgentRotateTokenView.as_view(), name="gateway-agent-rotate"),
]
