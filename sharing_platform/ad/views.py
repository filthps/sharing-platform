import re
import json
from typing import Optional
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils.translation import gettext
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, Subquery, OuterRef
from django.views.generic.base import TemplateView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer, HTMLFormRenderer, BrowsableAPIRenderer
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveDestroyAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_202_ACCEPTED, \
    HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_403_FORBIDDEN, HTTP_204_NO_CONTENT
from rest_framework.exceptions import PermissionDenied
from .models import AdItem, ExchangeProposal
from .serializers import AdItemSerializer, ChangeStatusExchangeProposalSerializer, InitialExchangeProposalSerializer, \
    OfferListSerializer, ExchangeInitListSerializer


class RequestTools:
    @staticmethod
    def _is_ajax_request(request: Request):
        if not isinstance(request, Request):
            raise TypeError
        if request.query_params.get("format", None) == "json":
            return True
        return False


class ShowAdItem(APIView, RequestTools):
    """ Страница показа предмета. """
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer)

    def get(self, request, id_):
        ad_item = AdItem.objects.filter(id=id_)
        if not ad_item.count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            if request.user.is_authenticated:
                return HttpResponseRedirect(redirect_to=reverse('all-ad-my'))
            return HttpResponseRedirect(redirect_to="all-ad")
        return Response(data={"ad": ad_item.first()},
                        template_name="ad/show_item.html",
                        status=HTTP_200_OK)


class CatalogPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = 'page_size'
    max_page_size = 1


class AdCatalog(ListAPIView, APIView, RequestTools):
    """ Перечень всех предметов с разнообразными фильтрами. """
    serializer_class = AdItemSerializer
    pagination_class = CatalogPagination
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer,)

    def get_queryset(self):
        if self.request.get_full_path().endswith("/all-my-items/"):
            return AdItem.objects.filter(owner=self.request.user)
        if self.request.get_full_path().endswith("/my/"):  # Получение списка предметов (мои предложения, адресованные другим предметам)
            return AdItem.objects.filter(id__in=ExchangeProposal.objects.filter(status="p").prefetch_related("sender").filter(
                                             sender__owner_id=self.request.user.id).values("sender_id")
                                         )
        if self.request.get_full_path().endswith("/tome/"):  # Получение списка предметов (предложения для меня)
            return AdItem.objects.filter(id__in=ExchangeProposal.objects.filter(status="p").select_related("receiver").filter(
                receiver__owner_id=self.request.user.id).values("receiver_id")
                                         )
        if self.request.get_full_path().endswith("/request/"):  # Список предметов, которым можно предложить обмен (я не жду одобрения) и не отправлял заявок
            big_query = ExchangeProposal.objects.filter(status="p").prefetch_related("sender").prefetch_related("receiver").exclude(
                sender__owner_id=self.request.user.id,
                receiver__owner_id=self.request.user.id)
            return AdItem.objects.exclude(
                owner=self.request.user).exclude(
                id__in=big_query.values("sender__id")).exclude(
                id__in=big_query.values("receiver__id")
            )
        return AdItem.objects.all()

    def filter_queryset(self, queryset):
        keywords = json.loads(self.request.GET.get("keys", "[]"))  # Ключевые слова в заголовке или описании
        category = self.request.GET.get("cat", None)  # Категория
        status = self.request.GET.get("status", None)  # Состояние
        if keywords:
            return queryset.filter(Q(name__contains=keywords) | Q(description__contains=keywords))
        if category:
            return queryset.filter(category__name=category)
        if status:
            return queryset.filter(status=status)
        return queryset

    def get(self, request, *args, **kwargs):
        if not self.__is_valid_params(request.GET):
            if self._is_ajax_request(request):
                return Response(status=HTTP_422_UNPROCESSABLE_ENTITY)
            return HttpResponseRedirect(status=HTTP_422_UNPROCESSABLE_ENTITY, redirect_to=request.get_full_path())
        resp_instance: Response = self.list(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(data=resp_instance.data["results"], headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/ad-items-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"items": resp_instance.data, "current_page_num": request.GET.get("page", 1)})

    @staticmethod
    def __is_valid_params(request_data: dict):
        """ Валидация необязательных параметров,
        входящих в строку запроса, начинающихся после символа '?',
        группируемые по символу '&'. """
        keyword = request_data.get("keys", None)
        if keyword is not None:
            keyword = re.sub(r"\W", keyword, "")
            keyword = keyword.replace(", ", ",")
            keyword = keyword.split(",")
            try:
                parsed = json.loads(f'{keyword}')
            except json.JSONDecodeError:
                return False
            if not parsed:
                return False  # Пустой список ключевых слов
        status = request_data.get("status", None)
        if status is not None:
            if status not in ["a", "b", "n"]:
                return False
        category = request_data.get("cat", None)
        if category is not None:
            if not category:
                return False
        if set(request_data) - {"keys", "cat", "status", "format", "page"}:
            return False  # Посторонние параметры
        return True


class CreateAd(CreateAPIView, TemplateView, RequestTools):
    """ Добавить в каталог товар предмет для обмена. """
    queryset = AdItem
    serializer_class = AdItemSerializer
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer, HTMLFormRenderer,)
    parser_classes = (MultiPartParser, FormParser,)
    permission_classes = (IsAuthenticated,)
    template_name = "ad/add_ad.html"
    extra_context = {"serializer": AdItemSerializer}

    def get_serializer(self, *args, **kwargs):
        serializer = self.get_serializer_class()
        return serializer(*args, request_user=self.request.user, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        if not serializer.is_valid():
            return Response(data={"serializer": serializer}, status=HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(data={"serializer": serializer}, status=HTTP_201_CREATED, headers=headers)


class OfferExchange(CreateAPIView, RequestTools):
    """ Инициировать предложение обмена. Предложить товар на обмен. """
    serializer_class = InitialExchangeProposalSerializer
    queryset = ExchangeProposal
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)

    def __init__(self, *a, **kw):
        self.sender = None
        self.receiver = None
        super().__init__(*a, **kw)

    def get_serializer(self, *args, **kwargs):
        serializer = self.get_serializer_class()
        return serializer(*args, request_user=self.request.user,
                          sender=self.sender.first(), receiver=self.receiver.first(), **kwargs)

    def create(self, request, *args, **kwargs):
        if not self.sender.count() or not self.receiver.count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            messages.add_message(request, messages.ERROR, gettext("ad_not_fount"))
            return HttpResponseRedirect(redirect_to=reverse("all-ad"))
        if ExchangeProposal.objects.filter(sender_id=self.sender.first().id, receiver_id=self.receiver.first().id,
                                           sender__owner_id=request.user.id, status="p").count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_422_UNPROCESSABLE_ENTITY)
            messages.add_message(request, messages.ERROR, gettext("ex_already_exist"))
            return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": kwargs["my_ad"]}))
        serializer = self.get_serializer(data={"sender": self.sender.first().id,
                                               "receiver": self.receiver.first().id,
                                               "status": "p"})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        if self._is_ajax_request(request):
            return Response(status=HTTP_201_CREATED, headers=headers, data=serializer.data)
        messages.add_message(request, messages.INFO, gettext("ex_offer_send_successful"))
        return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": kwargs["my_ad"]}), headers=headers)

    def post(self, request, *args, **kwargs):
        self.sender, self.receiver = AdItem.objects.filter(id=kwargs["my_ad"]),\
                                     AdItem.objects.filter(id=kwargs["other_ad"])
        return super().post(request, *args, **kwargs)


class OfferCancel(RetrieveUpdateDestroyAPIView, RequestTools):
    """ Отменить свой запрос на обмен, пока его не приняли или не отклонили. """
    queryset = ExchangeProposal.objects.filter(status="p")
    permission_classes = (IsAuthenticated,)

    def __init__(self, *a, **k):
        self.id = None
        super().__init__(*a, **k)

    def get_object(self):
        return self.get_queryset().filter(id=self.id)

    def check_object_permissions(self, request, obj: ExchangeProposal):
        if not obj.sender.id == request.user.id:
            raise PermissionDenied

    def delete(self, request, *args, **kwargs):
        self.id = kwargs["id_"]
        resp = super().delete(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(status=resp.status_code, headers=resp.headers)
        if resp.status_code == HTTP_403_FORBIDDEN:
            messages.add_message(request, messages.SUCCESS, gettext("offer_deleted"))
        return HttpResponseRedirect(redirect_to=reverse("all-ad"))


class ExchangeAdItem(RetrieveUpdateDestroyAPIView, RequestTools):
    """ Отклонить или принять предложение обмена. """
    queryset = ExchangeProposal.objects.filter(status="p")
    serializer_class = ChangeStatusExchangeProposalSerializer
    permission_classes = (IsAuthenticated,)

    def __init__(self, *a, **k):
        self.current_exchange_item: Optional[ExchangeProposal] = None  # Экземпляр текущей "сделки"
        super().__init__(*a, **k)

    def filter_queryset(self, queryset, exchangeProposal_pk):
        cur = current_exchange_item = queryset.filter(id=exchangeProposal_pk)
        self.current_exchange_item = cur.first()
        return cur

    def update(self, request: Request, *args, **kwargs):
        if not self.__check_permissions(request, kwargs["id_"]):
            if self._is_ajax_request(request):
                return Response(status=HTTP_422_UNPROCESSABLE_ENTITY)
            return HttpResponseRedirect(redirect_to=reverse("all-ad-my"))
        instance = self.filter_queryset(self.get_queryset(), kwargs["id_"])
        if not instance.count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_400_BAD_REQUEST)
            return HttpResponseRedirect(redirect_to=reverse("all-ad-my"))
        serializer = self.get_serializer(instance.first(),
                                         data={"status": {"accept": "s", "reject": "r"}[kwargs["type_"]]},
                                         partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            if serializer.data["status"] == "s":
                self.__change_ad_item_owner(self.current_exchange_item.sender, self.current_exchange_item.receiver)
                self.current_exchange_item.sender.save()
                self.current_exchange_item.receiver.save()
        if self._is_ajax_request(request):
            return Response(status=HTTP_202_ACCEPTED)
        return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": kwargs["id_"]}),
                                    status=HTTP_202_ACCEPTED)

    @staticmethod
    def __change_ad_item_owner(item_send: AdItem, item_received: AdItem):
        """ В случае, если обмен состоялся, у 2 экземпляров сущности предмета хозяева меняются местами. """
        item_send.owner, item_received.owner = item_received.owner, item_send.owner

    @staticmethod
    def __check_permissions(request, pk):
        if not request.user.is_authenticated:
            raise PermissionDenied
        owner = ExchangeProposal.objects.filter(
            id=pk, status="p").select_related("receiver").values("receiver__owner_id")
        if not owner.count():
            return False
        if not request.user.id == owner.first()["receiver__owner_id"]:
            raise PermissionDenied("only_receiver_can_accept_or_reject")
        return True


class ExchangeAdList(ListAPIView, APIView, RequestTools):
    """  Представление списка рассмотрения предложений,
    или отправки предложений обменять текущий предмет на один из списка...
    Предметы, которые я могу предложить взамен на интересующий. Или ответить на входящую заявку. """
    serializer_class = OfferListSerializer
    pagination_class = CatalogPagination
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer,)
    permission_classes = (IsAuthenticated,)

    def __init__(self, *args, **kwargs):
        self.current_ad_id = None  # Интересующий предмет, который я предлагаю обменять или готов принять
        self.type = None  # Предлагаю или принимаю предмет, или являюсь посторонним зрителем
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return ExchangeProposal.objects.prefetch_related("sender", "receiver")

    def filter_queryset(self, queryset):
        """ Взяли все АКТИВНЫЕ обмены с участием нашего предмета. Мы знаем, что инициатор обмена sender,
            если его sender.owner==request.user.id,
        то я был инициатором и теперь нужно показать форму отмены запроса,
            если receiver.owner==request.user.id,
        то моему предмету предложили обмен и нужно показать форму [принять/отказаться],
            если ни sender.owner!=request.user.id, ни receiver.owner==request.user.id,
        то можно показать форму предложения обмена
          """
        query = queryset.filter(status="p")
        if self.type == "in":  # Входящие заявки (согласиться/отказаться) менять этот предмет
            return query.filter(receiver_id=self.current_ad_id).annotate(
                receiver_is_request_user=Q(receiver__owner_id=self.request.user.id),
                username_sender=Subquery(User.objects.filter(id=OuterRef("sender_id__owner_id")).values_list("username")),
                username_receiver=Subquery(User.objects.filter(id=OuterRef("receiver_id__owner_id")).values_list("username"))
            )
        if self.type == "out":  # Исходящие заявки (Предложить обмен/отказаться от своего предложения)
            return query.filter(sender_id=self.current_ad_id).annotate(
                sender_is_request_user=Q(sender__owner_id=self.request.user.id),
                username_sender=Subquery(User.objects.filter(id=OuterRef("sender_id__owner_id")).values_list("username")),
                username_receiver=Subquery(User.objects.filter(id=OuterRef("receiver_id__owner_id")).values_list("username"))
            )
        if self.type == "all":  # Посторонний наблюдатель
            return query.filter(
                Q(receiver_id=self.current_ad_id) | Q(sender_id=self.current_ad_id)
            ).annotate(
                receiver_is_request_user=Q(receiver__owner_id=self.request.user.id),
                sender_is_request_user=Q(sender__owner_id=self.request.user.id),
                username_sender=Subquery(User.objects.filter(id=OuterRef("sender_id__owner_id")).values_list("username")),
                username_receiver=Subquery(User.objects.filter(id=OuterRef("receiver_id__owner_id")).values_list("username"))
            )
        return query

    def get(self, request, id_, type_, *args, **kwargs):
        self.current_ad_id = id_
        self.type = type_
        if not AdItem.objects.filter(id=id_).count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            messages.add_message(request, messages.ERROR, gettext("does_not_exist"))
            return HttpResponseRedirect(redirect_to=reverse("all-ad"))
        resp_instance: Response = self.list(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(data=json.dumps(resp_instance.data), headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/make-offer-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"items": resp_instance.data, "target_ad_id": self.current_ad_id, "type": self.type})


class ExchangeInitList(ListAPIView, APIView, RequestTools):
    """ Представление списка вещей, которым можно предложить обмен или отказаться от своего предложения """
    serializer_class = ExchangeInitListSerializer
    pagination_class = CatalogPagination
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer,)
    permission_classes = (IsAuthenticated,)
    queryset = AdItem

    def __init__(self, *args, **kwargs):
        self.my_ad_id = None  # Интересующий предмет, который я предлагаю обменять или готов принять
        self.type = None  # Предлагаю или принимаю предмет, или являюсь посторонним зрителем
        super().__init__(*args, **kwargs)

    def filter_queryset(self, queryset):
        return AdItem.objects.filter(owner_id=self.request.user.id).annotate(
            is_has_my_request=Q(exchange__sender_id=self.request.user.id) & Q(exchange__status="p"),  # Предлагал ни я этот предмет
        )

    def get(self, request, id_, *args, **kwargs):
        self.my_ad_id = id_
        if not AdItem.objects.filter(id=id_).count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            messages.add_message(request, messages.ERROR, gettext("does_not_exist"))
            return HttpResponseRedirect(redirect_to=reverse("all-ad"))
        resp_instance: Response = self.list(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(data=json.dumps(resp_instance.data), headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/ad-items-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"items": resp_instance.data, "target_ad_id": self.my_ad_id, "show_form": True})


""" Дальше пойдут представления для получения сугубо JSON данных через browser api """


class ItemProfileInputExchange(ListAPIView, RequestTools):
    permission_classes = (IsAuthenticated,)
    pagination_class = ...
    parser_classes = (JSONParser,)
    queryset = ExchangeProposal

    def __init__(self, *args, **kwargs):
        self.id = None
        super().__init__(*args, **kwargs)

    def filter_queryset(self, queryset):
        return queryset.objects.filter(
            receiver_id=self.id, status="p").select_related("sender")

    def get(self, request, *args, **kwargs):
        self.id = request.query_params.get
        if self._is_ajax_request(request):
            pass
        return


class ItemProfileOutputExchange(ListAPIView, RequestTools):
    permission_classes = (IsAuthenticated,)
    pagination_class = ...
    queryset = ExchangeProposal

    def __init__(self, *args, **kwargs):
        self.id = None
        super().__init__(*args, **kwargs)

    def filter_queryset(self, queryset):
        return queryset.objects.filter(
            sender_id=self.id, status="p").select_related("receiver").values("id", "receiver")

    def get(self, request, *args, **kwargs):
        self.id = request.query_params.get
        if self._is_ajax_request(request):
            pass
        return
