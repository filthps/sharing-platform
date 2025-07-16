import json
import re
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import TemplateView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer, HTMLFormRenderer
from rest_framework.generics import ListAPIView, GenericAPIView, CreateAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_202_ACCEPTED, HTTP_400_BAD_REQUEST
from django.db.models import Q
from .models import AdItem, ExchangeProposal
from .serializers import AdItemSerializer, ExchangeProposalSerializer
from django.core.validators import ValidationError


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

    def get(self, *_, id_):
        if id_ is None:
            return
        entry = AdItem.objects.filter(id=id_)
        if not entry.count():
            return Response(status=HTTP_404_NOT_FOUND)
        return Response(template_name="ad/show_item.html", data={"data": entry}, status=HTTP_200_OK)


class AdCatalog(ListAPIView, APIView):
    serializer_class = AdItemSerializer
    #renderer_classes = (JSONRenderer, TemplateHTMLRenderer)

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
        print(request.GET)
        if not self.__is_valid_params(request.GET):
            return Response(status=HTTP_422_UNPROCESSABLE_ENTITY)
        return super().get(request, *args, **kwargs)

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
        serializer.request_user = self.request.user
        return serializer(*args, **kwargs)


class CreateExchangeProposal(CreateAPIView, RequestTools):
    """ Инициировать предложение обмена. """
    serializer_class = ExchangeProposalSerializer
    queryset = ExchangeProposal
    renderer_classes = (HTMLFormRenderer, JSONRenderer)

    def get_renderer_context(self):
        pass

    def create(self, request, *args, **kwargs):
        pass


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
        return HttpResponseRedirect(redirect_to=reverse("show-ad", self.request.query_params["id_"]), status=HTTP_202_ACCEPTED)
