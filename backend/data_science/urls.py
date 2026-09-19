from rest_framework.routers import DefaultRouter
from .views import DatasetDefinitionViewSet, ModelDefinitionViewSet, ModelRunViewSet, ModelVersionViewSet, PredictionAssetViewSet, PythonTransformationViewSet
router=DefaultRouter()
router.register("python-transformations",PythonTransformationViewSet,basename="python-transformation")
router.register("datasets",DatasetDefinitionViewSet,basename="dataset")
router.register("models",ModelDefinitionViewSet,basename="ml-model")
router.register("runs",ModelRunViewSet,basename="ml-run")
router.register("versions",ModelVersionViewSet,basename="ml-version")
router.register("predictions",PredictionAssetViewSet,basename="prediction")
urlpatterns=router.urls
