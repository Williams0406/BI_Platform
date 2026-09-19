from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .services import (
    database_metrics,
    execution_metrics,
    gateway_metrics,
    redis_health,
)
from .storage import healthcheck as storage_healthcheck


@api_view(["GET"])
@permission_classes([IsAdminUser])
def operational_status(request):
    return Response(
        {
            "database": database_metrics(),
            "redis": redis_health(),
            "storage": storage_healthcheck(),
            "executions": execution_metrics(),
            "gateways": gateway_metrics(),
            "artifact_backend": settings.ARTIFACT_STORAGE_BACKEND,
        }
    )
