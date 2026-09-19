from django.urls import path

from .views import (
    DataSourceCatalogPreviewView,
    DataSourceReadPageView,
    DataSourceTestConnectionView,
)

app_name = "connectors"

urlpatterns = [
    path(
        "sources/<uuid:pk>/test/",
        DataSourceTestConnectionView.as_view(),
        name="source-test",
    ),
    path(
        "sources/<uuid:pk>/catalog/",
        DataSourceCatalogPreviewView.as_view(),
        name="source-catalog",
    ),
    path(
        "sources/<uuid:pk>/read/",
        DataSourceReadPageView.as_view(),
        name="source-read",
    ),
]
