from django.urls import include,path
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet,DataSourceSecretViewSet,DestructiveChangeRequestViewSet,ResourcePermissionViewSet,WorkspaceGovernanceViewSet,DataCopyEventViewSet

router=DefaultRouter()
router.register("audit",AuditLogViewSet,basename="audit")
router.register("permissions",ResourcePermissionViewSet,basename="resource-permission")
router.register("workspaces",WorkspaceGovernanceViewSet,basename="workspace-governance")
router.register("destructive-requests",DestructiveChangeRequestViewSet,basename="destructive-request")
router.register("copy-events",DataCopyEventViewSet,basename="copy-event")

secret_list=DataSourceSecretViewSet.as_view({"get":"list"})
secret_detail=DataSourceSecretViewSet.as_view({"get":"retrieve"})
secret_create=DataSourceSecretViewSet.as_view({"post":"create"})

urlpatterns=[
    path("",include(router.urls)),
    path("datasource-secrets/",DataSourceSecretViewSet.as_view({"get":"list","post":"create"}),name="datasource-secret-list"),
    path("datasource-secrets/<uuid:pk>/",secret_detail,name="datasource-secret-detail"),
]
