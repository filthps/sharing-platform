from django.urls import path, re_path
from .views import ShowAdItem, AdCatalog, CreateAd, ExchangeAdItems

urlpatterns = [
    path("show/<uuid:id_>/", ShowAdItem.as_view(), name="show-ad"),  # Получение расширенных данных о предмете обмена
    path("catalog/my/", AdCatalog.as_view(), name="all-ad"),  # Получение списка предметов
    path("catalog/tome/", AdCatalog.as_view(), name="all-ad"),  # Получение списка предметов
    path("catalog/", AdCatalog.as_view(), name="all-ad"),  # Получение списка предметов
    path("post/", CreateAd.as_view(), name="post-ad"),
    re_path(r"exchange/(?P<type_>(accept|reject))/(?P<id_>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/",
            ExchangeAdItems.as_view(),  name="exchange-items")  # Совершить обмен/отклонить обмен
]
