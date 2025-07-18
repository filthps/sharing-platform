from django.urls import path, re_path
from .views import ShowAdItem, AdCatalog, CreateAd, ExchangeAdItem, OfferExchange, ExchangeCatalog, ShowAdItemReceivers

urlpatterns = [
    path("show/<uuid:id_>/", ShowAdItem.as_view(), name="show-ad"),  # Получение расширенных данных о предмете обмена
    path("my-item/<uuid:id_>/exchanges/(?P<type_>my|tome)/", ShowAdItemReceivers.as_view(), name="my-ad-exchanges"),  # Предложения мне взамен данному предмету
    path("catalog/my/", AdCatalog.as_view(), name="all-ad-my"),  # Получение списка предметов (мои предложения, адресованные другим предметам)
    path("catalog/tome/", AdCatalog.as_view(), name="all-ad-tome"),  # Получение списка предметов (предложения для меня)
    path("catalog/request/", AdCatalog.as_view(), name="all-ad-can_request"),  # Список предметов, которым можно предложить обмен
    path("catalog/all-my-items/", AdCatalog.as_view(), name="all-ad-my-ad-items"),
    path("catalog/", AdCatalog.as_view(), name="all-ad"),  # Получение списка всех предметов
    path("post/", CreateAd.as_view(), name="post-ad"),  # Добавить предмет
    path("offer/<uuid:my_ad>/<uuid:other_ad>/", OfferExchange.as_view(), name="exchange-offer"),  # Предложить свой предмет на обмен
    path("<uuid:id_>/pending/", ExchangeCatalog.as_view(), name="pending-items-on-current"),  # Показ желающих на обмен ЭТОГО предмета на свой (в настоящем времени status всё ещё в ожидании)
    path("<uuid:id_>/rejected/", ExchangeCatalog.as_view(), name="rejected-item-on-current"),  # История отклонённых обменов данного предмета
    path("<uuid:id_>/accepted/", ExchangeCatalog.as_view(), name="accepted-items-on-current"),  # История успешных обменов данного предмета
    path("<uuid:id_>/all-exchanges/", ExchangeCatalog.as_view(), name="all-exchanges-items-on-current"),  # Все "события", связанные с обменом данного предмета
    re_path(r"exchange/(?P<type_>accept|reject)/(?P<id_>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/",
            ExchangeAdItem.as_view(),  name="exchange-response"),  # Совершить обмен/отклонить обмен
]
