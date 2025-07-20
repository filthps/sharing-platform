from rest_framework.parsers import JSONParser
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .serializers import AdBulkSerializer, AdItemSerializer
from ad.models import AdItem


class AdItemsJsonLoader(ListCreateAPIView):
    serializer_class = AdBulkSerializer
    parser_classes = (JSONParser,)
    permission_classes = (IsAdminUser,)

    def create(self, request, *args, **kwargs):
        print(request.data)
        if "ads" not in request.data:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = AdItemSerializer(data=request.data["ads"], many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
