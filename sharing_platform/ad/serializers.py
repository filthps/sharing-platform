import uuid
from rest_framework import serializers
from .models import AdItem, ExchangeProposal, uuid_validator, exchange_item_validator


def check_exchange_item_status(value):
    if value not in ["s", "r"]:
        raise serializers.ValidationError


class AdItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdItem
        fields = "__all__"

    def __init__(self, *a, request_user=None, **k):
        self.request_user = request_user
        super().__init__(*a, **k)
    id = serializers.CharField(read_only=True)
    add_by = serializers.HiddenField(default=None)

    def create(self, validated_data):
        user = getattr(self, "request_user", None)
        if user is None:
            raise ValueError
        validated_data.update({"add_by": user})
        return super().create(validated_data)


class ExchangeProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeProposal
        fields = "__all__"
        exclude = ("status", "created_at",)

    def __init__(self, *a, request_user=None, **k):
        self.request_user = request_user
        super().__init__(*a, **k)
    id = serializers.HiddenField(default=uuid.uuid4())
    sender_ad = serializers.HiddenField(default=None)

    def create(self, validated_data):
        user = getattr(self, "request_user", None)
        if user is None:
            raise ValueError
        validated_data.update({"sender_ad": user})
        return super().create(validated_data)
