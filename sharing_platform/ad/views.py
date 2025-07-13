from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK
from .models import AdItem
from .serializers import AdItemSerializer


class ShowAdItem(APIView):
    serializer_class = AdItemSerializer
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer)
    allowed_methods = ("GET", "POST",)

    def get(self, *_, id_):
        if id_ is None:
            return
        entry = AdItem.objects.filter(id=id_)
        if not entry.count():
            return Response(status=HTTP_404_NOT_FOUND)
        return Response(template_name="ad/show_item.html", data={"data": entry}, status=HTTP_200_OK)
