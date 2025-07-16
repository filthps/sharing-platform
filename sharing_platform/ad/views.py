import json
import re
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q
from django.views.generic.base import TemplateView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer, HTMLFormRenderer
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from .models import AdItem, ExchangeProposal
from .serializers import AdItemSerializer, ExchangeProposalSerializer


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
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer, HTMLFormRenderer)

    def get(self, request, id_):
        if id_ is None:
            return
        ad_entry = AdItem.objects.filter(id=id_)
        if not ad_entry.count():
            return Response(status=HTTP_404_NOT_FOUND)
        input_proposals = ExchangeProposal.objects.filter(receiver_ad__id=id_, status="p")
        prop_already_sent = ExchangeProposal.objects.select_related("receiver_ad").filter(receiver_ad__id=request.user.id)  # Предложения на чужие вещи, инициированные мной
        return Response(template_name="ad/show_item.html",
                        data={"ad": ad_entry,
                              "has_input_exchange": input_proposals.count(),
                              "my_ex": prop_already_sent},
                        status=HTTP_200_OK)


class CatalogPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 12


class AdCatalog(ListAPIView, APIView, RequestTools):
    serializer_class = AdItemSerializer
    pagination_class = CatalogPagination
    renderer_classes = (TemplateHTMLRenderer,)

    def get_queryset(self):
        if self.request.get_full_path().endswith("my/"):
            return AdItem.objects.filter(add_by__id=self.request.user.id)
        if self.request.get_full_path().endswith("tome/"):
            return AdItem.objects.filter(id__in=ExchangeProposal.objects.select_related(
                "receiver_ad").filter(receiver_ad__add_by__id=self.request.user.id).values("receiver_ad__id"))
        return AdItem.objects.all()

    def filter_queryset(self, queryset):
        keywords = json.loads(self.request.GET.get("keys", "[]"))  # Ключевые слова в заголовке или описании
        category = self.request.GET.get("cat", None)  # Категория
        status = self.request.GET.get("status", None)  # Состояние
        if keywords:
            queryset = queryset.filter(Q(name__contains=keywords) | Q(description__contains=keywords))
        if category:
            queryset = queryset.filter(category__name=category)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get(self, request, *args, **kwargs):
        if not self.__is_valid_params(request.GET):
            if self._is_ajax_request(request):
                return Response(status=HTTP_422_UNPROCESSABLE_ENTITY)
            return HttpResponseRedirect(status=HTTP_422_UNPROCESSABLE_ENTITY, redirect_to=request.get_full_path())
        resp_instance: Response = self.list(request, *args, **kwargs)
        print(resp_instance.data)
        if self._is_ajax_request(request):
            return Response(data=json.dumps(resp_instance.data), headers=resp_instance.headers, status=HTTP_200_OK)
        return Response(template_name="ad/ad-items-list.html", status=HTTP_200_OK, headers=resp_instance.headers,
                        data={"form": resp_instance.data})

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
        if set(request_data) - {"keys", "cat", "status", "format"}:
            return False  # Посторонние параметры
        return True


class CreateAd(CreateAPIView, TemplateView):
    """ Добавить в каталог товар предмет для обмена. """
    queryset = AdItem
    serializer_class = AdItemSerializer
    renderer_classes = (JSONRenderer, HTMLFormRenderer)
    parser_classes = (JSONParser, FormParser,)
    template_name = "ad/add_ad.html"
    extra_context = {"form": AdItemSerializer}

    def get_serializer(self, *args, **kwargs):
        serializer = self.get_serializer_class()
        return serializer(*args, request_user=self.request.user, **kwargs)


class CreateExchangeProposal(CreateAPIView, RequestTools):
    """ Инициировать предложение обмена. Предложить товар на обмен. """
    serializer_class = ExchangeProposalSerializer
    queryset = ExchangeProposal
    renderer_classes = (HTMLFormRenderer, JSONRenderer)

    def get_serializer(self, *args, **kwargs):
        serializer = self.get_serializer_class()
        return serializer(*args, request_user=self.request.user, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        if self._is_ajax_request(request):
            return Response(status=HTTP_201_CREATED, headers=headers)
        return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": self.request.query_params["id_"]}),
                                    status=HTTP_201_CREATED, headers=headers)


class ExchangeAdItems(UpdateAPIView, RequestTools):
    """ Отклонить или принять предложение обмена. """
    queryset = ExchangeProposal.objects.filter(status="p")
    serializer_class = ExchangeProposalSerializer

    def filter_queryset(self, queryset):
        return queryset.filter(id=self.request.query_params["id_"])

    def check_object_permissions(self, request, obj):
        if not request.user.id == obj.sender_ad__id:
            self.permission_denied(self.request, "you_can't_exchange_with_yourself", 20)

    def update(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(*args, **kwargs)
        instance = self.filter_queryset(self.get_queryset())
        if not instance.count():
            if self._is_ajax_request(request):
                return Response(status=HTTP_400_BAD_REQUEST)
            return Response()
        serializer = serializer(instance, data={"status": request.query_params["type_"]}, partial=True)
        serializer.save()
        if self._is_ajax_request(request):
            return Response(status=HTTP_202_ACCEPTED)
        return HttpResponseRedirect(redirect_to=reverse("show-ad", kwargs={"id_": self.request.query_params["id_"]}),
                                    status=HTTP_202_ACCEPTED)
