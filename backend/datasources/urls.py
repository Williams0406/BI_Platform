from rest_framework.routers import DefaultRouter
from .views import DataAssetViewSet, DataSourceViewSet, SourceBindingViewSet, PublishPlanViewSet, WritebackPolicyViewSet
router=DefaultRouter()
router.register("sources",DataSourceViewSet,basename="data-source")
router.register("assets",DataAssetViewSet,basename="data-asset")
router.register("source-bindings",SourceBindingViewSet,basename="source-binding")
router.register("publish-plans",PublishPlanViewSet,basename="publish-plan")
router.register("writeback-policies",WritebackPolicyViewSet,basename="writeback-policy")
urlpatterns=router.urls
