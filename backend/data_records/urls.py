from django.urls import path

from .views import RecordCollectionView, RecordDetailView

app_name = "data_records"

urlpatterns = [
    path(
        "tables/<uuid:table_pk>/",
        RecordCollectionView.as_view(),
        name="record-collection",
    ),
    path(
        "tables/<uuid:table_pk>/<str:record_key>/",
        RecordDetailView.as_view(),
        name="record-detail",
    ),
]
