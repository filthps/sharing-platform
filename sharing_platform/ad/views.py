import re
import json
from typing import Optional
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext
from django.urls import reverse
from django.db import transaction
from django.db.models import Q
from django.views.generic.base import TemplateView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer, HTMLFormRenderer, BrowsableAPIRenderer
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_202_ACCEPTED, \
    HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from rest_framework.exceptions import PermissionDenied
from .models import AdItem, ExchangeProposal
from .serializers import AdItemSerializer, ChangeStatusExchangeProposalSerializer, InitialExchangeProposalSerializer


class RequestTools:
    @staticmethod
    def _is_ajax_request(request: Request):
        if not isinstance(request, Request):
            raise TypeError
        i = request.META.get("X-Requested_With", None)
        if i is None:
            return False
        if i == "XMLHTTPRequest":
            return True
        return False


class ShowAdItem(APIView):
    """ Страница показа предмета. """
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer)

    def get(self, request, id_):
        ad_entry = AdItem.objects.filter(id=id_)
        input_exchange_items = ExchangeProposal.objects.filter(receiver_ad_id=id_, status="p")
        output_exchange_items = ExchangeProposal.objects.exclude(receiver_ad_id=id_, status="p")
        if not ad_entry.count():
            return Response(status=HTTP_404_NOT_FOUND)
        is_mine_ad_item = True if ad_entry.first().owner == request.user.id else False
        return Response(data={"ad": ad_entry.first(), "input_ex": input_exchange_items,
                              "output_ex": output_exchange_items, "is_mine_ad_item": is_mine_ad_item},
                        template_name="ad/show_item.html",
                        status=HTTP_200_OK)


class CatalogPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 6


class AdCatalog(ListAPIView, APIView, RequestTools):
    """ Перечень всех предметов с разнообразными фильтрами. """
    serializer_class = AdItemSerializer
    pagination_class = CatalogPagination
    renderer_classes = (TemplateHTMLRenderer,)

    def get_queryset(self):
        if self.request.get_full_path().endswith("/all-my-items/"):
            return AdItem.objects.filter(owner=self.request.user)
        if self.request.get_full_path().endswith("/my/"):  # Получение списка предметов (мои предложения, адресованные другим предметам)
            return AdItem.objects.filter(status="p",
                                         id__in=ExchangeProposal.objects.prefetch_related("sender_ad").filter(
                                             sender_ad__owner_id=self.request.user.id).values("sender_ad__id")
                                         )
        if self.request.get_full_path().endswith("/tome/"):  # Получение списка предметов (предложения для меня)
            return AdItem.objects.filter(status="p",
                                         id__in=ExchangeProposal.objects.select_related("receiver_ad").filter(
                                            receiver_ad__owner_id=self.request.user.id).values("receiver_ad__id")
                                        )
        if self.request.get_full_path().endswith("/request/"):  # Список предметов, которым можно предложить обмен (я не жду одобрения)
            big_query = ExchangeProposal.objects.prefetch_related("sender_ad").prefetch_related("receiver_ad").exclude(
                sender_ad__owner_id=self.request.user.id,
                receiver_ad__owner_id=self.request.user.id)
            return AdItem.objects.exclude(
                owner=self.request.user).exclude(
                id__in=big_query.values("sender_ad__id")).exclude(
                id__in=big_query.values("receiver_ad__id")
            ).filter(status="p",)
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
        accept_forms = True if self.request.get_full_path().endswith("/tome/") else False  # Включить в шаблоне кнопки accept/reject
        send_ex_request_form = True if self.request.get_full_path().endswith("/request/") else False  # включить в шаблоне кнопку "запросить обмен"
        if self._is_ajax_request(request):
            return Response(data=json.dumps(resp_instance.data), headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/ad-items-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"items": resp_instance.data, "accept_mini_form": accept_forms,
                              "send_ex_request_form": send_ex_request_form,
                              "current_page_num": request.GET.get("page", 1)})

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
            if status not in ["a", "b"]:
                return False
        category = request_data.get("cat", None)
        if category is not None:
            if not category:
                return False
        if set(request_data) - {"keys", "cat", "status", "format", "page"}:
            return False  # Посторонние параметры
        return True


class CreateAd(TemplateView, CreateAPIView, RequestTools):
    """ Добавить в каталог товар предмет для обмена. """
    queryset = AdItem
    serializer_class = AdItemSerializer
    renderer_classes = (TemplateHTMLRenderer, BrowsableAPIRenderer, JSONRenderer,)
    parser_classes = (MultiPartParser, FormParser,)
    template_name = "ad/add_ad.html"
    extra_context = {"serializer": AdItemSerializer}

    def get_serializer(self, *args, **kwargs):
        serializer = self.get_serializer_class()
        return serializer(*args, request_user=self.request.user, **kwargs)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(status=HTTP_201_CREATED, data=response.data, headers=response.headers)
        messages.add_message(request, messages.INFO, gettext("ad_added_successful"))
        return HttpResponseRedirect(redirect_to=reverse("show-ad", args=[response.data["id"]]))  # 302 redirect


class OfferExchange(CreateAPIView, RequestTools):
    """ Инициировать предложение обмена. Предложить товар на обмен. """
    serializer_class = InitialExchangeProposalSerializer
    queryset = ExchangeProposal
    renderer_classes = (JSONRenderer, HTMLFormRenderer,)
    parser_classes = (JSONParser, FormParser,)

    def get_serializer(self, *args, **kwargs):
        serializer = self.get_serializer_class()
        return serializer(*args, request_user=self.request.user, **kwargs)

    def create(self, request, *args, **kwargs):
        sender_ad_item, receiver_ad_item = \
            AdItem.objects.filter(id=request.query_params["my_ad"]), \
            AdItem.objects.filter(id=request.query_params["other_ad"])
        if not sender_ad_item.count() or not receiver_ad_item.count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            messages.add_message(request, messages.INFO, gettext("ad_not_fount"))
            return HttpResponseRedirect(redirect_to=reverse("all-ad"))
        serializer = self.get_serializer(data={"sender_ad": sender_ad_item.first(), "receiver_ad": receiver_ad_item})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        if self._is_ajax_request(request):
            return Response(status=HTTP_201_CREATED, headers=headers, data=json.dumps(serializer.data))
        messages.add_message(request, messages.INFO, gettext("ex_offer_send_successful"))
        return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": self.request.query_params["id_"]}),
                                    status=HTTP_201_CREATED, headers=headers)


class ExchangeAdItem(UpdateAPIView, RequestTools):
    """ Отклонить или принять предложение обмена. """
    queryset = ExchangeProposal.objects.filter(status="p")
    serializer_class = ChangeStatusExchangeProposalSerializer

    def __init__(self, *a, **k):
        self.current_exchange_item: Optional[ExchangeProposal] = None  # Экземпляр текущей "сделки"
        super().__init__(*a, **k)

    def filter_queryset(self, queryset):
        self.current_exchange_item = queryset.filter(id=self.request.query_params["id_"])
        return self.current_exchange_item

    def update(self, request: Request, *args, **kwargs):
        self.__check_permissions(request, kwargs["id_"])
        serializer = self.get_serializer(*args, **kwargs)
        instance = self.filter_queryset(self.get_queryset())
        if not instance.count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_400_BAD_REQUEST)
            return HttpResponseRedirect(redirect_to=reverse("all-ad-my"), status=HTTP_400_BAD_REQUEST)
        serializer = serializer(instance, data={"status": request.query_params["type_"]},
                                partial=True)
        with transaction.atomic():
            serializer.save()
            self.__change_ad_item_owner(self.current_exchange_item.sender_ad, self.current_exchange_item.receiver_ad)
            self.current_exchange_item.sender_ad.save()
            self.current_exchange_item.receiver_ad.save()
        if self._is_ajax_request(request):
            return Response(status=HTTP_202_ACCEPTED)
        return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": self.request.query_params["id_"]}),
                                    status=HTTP_202_ACCEPTED)

    @staticmethod
    def __change_ad_item_owner(item_send: AdItem, item_received: AdItem):
        """ В случае, если обмен состоялся, у 2 экземпляров сущности предмета хозяева меняются местами. """
        item_send.owner, item_received.owner = item_received.owner, item_send.owner

    @staticmethod
    def __check_permissions(request, pk):
        if not request.user.is_authenticated:
            raise PermissionDenied
        print(request.query_params)
        owner = ExchangeProposal.objects.filter(
            id=pk, status="p").select_related("receiver_ad")
        if not owner.count():
            return
        if not request.user.id == owner.first().receiver_ad_id:
            raise PermissionDenied("only_receiver_can_accept_or_reject")


class ExchangeCatalog(ListAPIView, APIView, RequestTools):
    """ Каталог предметов, представляющий связь(бизнес процесс обмена) этих предметов с переданным в url. 
    Неважно кто инициатор. """
    serializer_class = AdItemSerializer
    pagination_class = CatalogPagination
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer,)

    def __init__(self, *args, **kwargs):
        self.current_ad_id = None
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return AdItem.objects.filter(
            id__in=ExchangeProposal.objects.prefetch_related("sender_ad").filter(
                sender_ad_id=self.current_ad_id).values("sender_ad_id")).filter(id__in=ExchangeProposal.objects.prefetch_related("receiver_ad").filter(
                receiver_ad_id=self.current_ad_id).values("receiver_ad_id"))

    def filter_queryset(self, queryset):
        if self.request.get_full_path().endswith("/pending/"):  # Показ желающих на обмен ЭТОГО предмета на свой (в настоящем времени status всё ещё в ожидании)
            return queryset.filter(status="p")
        if self.request.get_full_path().endswith("/rejected/"):  # История отклонённых обменов данного предмета
            return queryset.filter(status="r")
        if self.request.get_full_path().endswith("/accepted/"):  # История успешных обменов данного предмета
            return queryset.filter(status="s")
        return queryset

    def get(self, request, id_, *args, **kwargs):
        self.current_ad_id = id_
        if not AdItem.objects.filter(id=id_).count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            messages.add_message(request, messages.ERROR, gettext("does_not_exist"))
            return HttpResponseRedirect(redirect_to=reverse("all-ad"))
        resp_instance: Response = self.list(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(data=json.dumps(resp_instance.data), headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/ad-items-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"items": resp_instance.data})


class ShowAdItemReceivers(ListAPIView, APIView, RequestTools):
    """ Список предложений по предмету (который фигурирует в URL). Инициатор некто другой. """
    serializer_class = AdItemSerializer
    pagination_class = CatalogPagination
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer,)
    
    def __init__(self, *args, **kwargs):
        self.current_ad_id = None
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return AdItem.objects.filter(status="p", id__in=ExchangeProposal.objects.prefetch_related(
            "receiver_ad").prefetch_related(
            "sender_id").filter(
            receiver_ad_id=self.current_ad_id).values("sender_ad_id"))
    
    def get(self, request, id_, *args, **kwargs):
        self.current_ad_id = id_
        if not AdItem.objects.filter(id=id_).count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_404_NOT_FOUND)
            messages.add_message(request, messages.ERROR, gettext("does_not_exist"))
            return HttpResponseRedirect(redirect_to=reverse("all-ad"))
        resp_instance: Response = self.list(request, *args, **kwargs)
        if self._is_ajax_request(request):
            return Response(data=json.dumps(resp_instance.data), headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/ad-items-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"items": resp_instance.data, "main_ad_item_id": self.current_ad_id,
                              "accept_mini_form": True})
