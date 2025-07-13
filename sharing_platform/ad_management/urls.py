from django.urls import path

urlpatterns = [
    path("post-ad/", name="post"),  # Опубликовать вещь для обмена
    path("respond/<uuid:id_>/", name="respond"),  # Принять/отклонить
    path("exchange/<uuid:sender_ad>/<uuid:receiver_ad>/", name="make-exchange"),  # Предложить обмен
    path("edit/<uuid:ad_id>/", name="edit"),
    path("delete/<uuid:ad_id>/", name="delete")
]
