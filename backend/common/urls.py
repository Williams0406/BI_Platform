from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import health_live, health_ready, root, ScriptBlockViewSet, ComputeTargetViewSet, PythonEnvironmentViewSet, EnvironmentPackageViewSet
app_name='common'
router=DefaultRouter(); router.register('scripts',ScriptBlockViewSet,basename='script-block'); router.register('compute-targets',ComputeTargetViewSet,basename='compute-target'); router.register('python-environments',PythonEnvironmentViewSet,basename='python-environment'); router.register('environment-packages',EnvironmentPackageViewSet,basename='environment-package')
urlpatterns=[path('',root,name='root'),path('health/live/',health_live,name='health-live'),path('health/ready/',health_ready,name='health-ready'),path('',include(router.urls))]
