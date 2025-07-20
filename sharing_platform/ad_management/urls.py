from django.urls import path
from .views import AdItemsJsonLoader

urlpatterns = [
    path("bulk-json-load/", AdItemsJsonLoader.as_view(), name="ad-json-loader")
]
