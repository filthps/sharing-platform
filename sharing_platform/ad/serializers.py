from rest_framework.serializers import ModelSerializer, Serializer
from .models import AdItem


class AdItemSerializer(ModelSerializer):
    class Meta:
        model = AdItem
        fields = "__all__"
