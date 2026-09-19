from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("common.urls")),
    path("api/v1/auth/", include("identity.urls")),
    path("api/v1/workspaces/", include("workspaces.urls")),
    path("api/v1/data/", include("datasources.urls")),
    path("api/v1/connectors/", include("connectors.urls")),
    path("api/v1/catalog/", include("data_model.urls")),
    path("api/v1/records/", include("data_records.urls")),
    path("api/v1/views/", include("views_engine.urls")),
    path("api/v1/transformations/", include("transformations.urls")),
    path("api/v1/dependencies/", include("dependencies.urls")),
    path("api/v1/executions/", include("execution.urls")),
    path("api/v1/metrics/", include("metrics.urls")),
    path("api/v1/analytics/", include("analytics.urls")),
    path("api/v1/data-science/", include("data_science.urls")),
    path("api/v1/optimization/", include("optimization.urls")),
    path("api/v1/import-export/", include("imports_exports.urls")),
    path("api/v1/governance/", include("governance.urls")),
    path("api/v1/gateway/", include("customer_gateway.urls")),
    path("api/v1/ops/", include("platform_ops.urls")),
]
