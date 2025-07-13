from django.urls import path
from .views import ShowAdItem

urlpatterns = [
    path("show/<uuid:id_>/", ShowAdItem.as_view(), name="show-ad"),  # Получение расширенных данных о предмете обмена
    #path("catalog/", name="all-ad"),  # Получение списка предметов

]
