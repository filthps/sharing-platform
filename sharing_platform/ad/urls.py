from django.urls import path, re_path
from .views import ShowAdItem, AdCatalog, CreateAd, ExchangeAdItem, OfferExchange, OfferCancel, ExchangeAdList, \
    ItemProfileInputExchange, ItemProfileOutputExchange, ExchangeInitList

urlpatterns = [
    path("show/<uuid:id_>/", ShowAdItem.as_view(), name="show-ad"),  # Получение расширенных данных о предмете обмена
    path("exchange-create-list/<uuid:id_>/", ExchangeInitList.as_view(), name="exchange-init-list"),  # Страница с одиночными элементами, где я предлагаю сделку
    path("catalog/my/", AdCatalog.as_view(), name="all-ad-my"),  # Получение списка предметов (мои предложения, адресованные другим предметам)
    path("catalog/tome/", AdCatalog.as_view(), name="all-ad-tome"),  # Получение списка предметов (предложения для меня)
    path("catalog/request/", AdCatalog.as_view(), name="all-ad-can_request"),  # Список предметов, которым можно предложить обмен
    path("catalog/all-my-items/", AdCatalog.as_view(), name="all-ad-my-ad-items"),
    path("catalog/", AdCatalog.as_view(), name="all-ad"),  # Получение списка всех предметов
    path("post/", CreateAd.as_view(), name="post-ad"),  # Добавить предмет
    path("offer/<uuid:my_ad>/<uuid:other_ad>/", OfferExchange.as_view(), name="exchange-offer"),  # Предложить свой предмет на обмен
    path("offer/<uuid:id_>/cancel/", OfferCancel.as_view(), name="destroy_offer"),  # Отозвать предложение на обмен
    re_path(r"exchange/(?P<type_>accept|reject)/(?P<id_>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/",
            ExchangeAdItem.as_view(),  name="exchange-response"),  # Совершить обмен/отклонить обмен
    re_path("exchange-request-list/(?P<id_>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P<type_>in|out|all)/",
            ExchangeAdList.as_view(), name="offer-request-list"),  # Список предметов, рассмотрение входящих предложений
    # Только browser api представления
    path("load-profile-input-ex/", ItemProfileInputExchange.as_view(), name="load-profile-input_ex"),
    path("load-profile-output-ex/", ItemProfileOutputExchange.as_view(), name="load-profile-output_ex")
]
