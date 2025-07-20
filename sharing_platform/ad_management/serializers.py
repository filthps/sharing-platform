from rest_framework import serializers
from ad.models import AdItem


class AdItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdItem
        exclude = ("id",)


class AdBulkSerializer(serializers.Serializer):
    ads = AdItemSerializer(many=True)
