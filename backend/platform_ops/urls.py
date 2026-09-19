from django.urls import path
from .views import operational_status

app_name = "platform_ops"

urlpatterns = [
    path("status/", operational_status, name="status"),
]
