from datetime import timedelta

from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.utils import timezone

from customer_gateway.models import GatewayRegistration
from execution.models import Execution
from .models import OperationalMetricSnapshot
from .storage import healthcheck as storage_healthcheck


def database_metrics():
    result = {"vendor": connection.vendor}
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
        if connection.vendor == "postgresql":
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            result["connections"] = int(cursor.fetchone()[0])
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE wait_event IS NOT NULL"
            )
            result["waiting_connections"] = int(cursor.fetchone()[0])
    return result


def redis_health():
    try:
        cache.set("ops:health", "ok", 10)
        return {"ok": cache.get("ops:health") == "ok"}
    except Exception as exc:
        return {"ok": False, "detail": exc.__class__.__name__}


def execution_metrics():
    rows = (
        Execution.objects.values("status")
        .annotate(count=Count("id"))
        .order_by()
    )
    return {row["status"]: row["count"] for row in rows}


def gateway_metrics():
    cutoff = timezone.now() - timedelta(minutes=5)
    return {
        "total": GatewayRegistration.objects.count(),
        "seen_last_5m": GatewayRegistration.objects.filter(
            last_seen_at__gte=cutoff
        ).count(),
        "revoked": GatewayRegistration.objects.filter(
            status=GatewayRegistration.Status.REVOKED
        ).count(),
    }


def snapshot_metrics():
    snapshot = OperationalMetricSnapshot.objects.create(
        api={"status": "ok"},
        database=database_metrics(),
        executions=execution_metrics(),
        gateways=gateway_metrics(),
        storage=storage_healthcheck(),
    )
    return snapshot
