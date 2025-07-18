import uuid
from django.utils.translation import gettext
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
    name = serializers.CharField(max_length=30, required=True)
    owner = serializers.HiddenField(default=None)

    def create(self, validated_data):
        user = getattr(self, "request_user", None)
        if user is None:
            raise ValueError
        validated_data.update({"owner": user})
        return super().create(validated_data)


class InitialExchangeProposalSerializer(serializers.ModelSerializer):
    """ Сериализатор инициализирущий предложение обмена. """
    class Meta:
        model = ExchangeProposal
        fields = "__all__"
        exclude = ("id", "status", "created_at")

    def __init__(self, *a, request_user=None, **k):
        self.request_user = request_user
        super().__init__(*a, **k)
    id = serializers.HiddenField(default=uuid.uuid4())
    sender_ad = serializers.HiddenField(default=None)

    def validate(self, attrs):
        user = getattr(self, "request_user", None)
        if user is None:
            raise ValueError("Атрибут экземпляра 'request_user' необходимо передать для валидации")
        if not attrs["sender_ad."].__owner_id == user.id:
            raise serializers.ValidationError(gettext("value_column_sender_ad_taken_current_user"))  # В качестве значения столбца sender_ad принимается предмет ПРЕДЛАГАЮЩЕГО пользователя (текущий request.user)
        if attrs["receiver_ad"].__owner_id == user.id:
            raise serializers.ValidationError(gettext("value_column_receiver_ad_cnt_be_self_user"))  # В качестве значения receiver_ad должен выступать потенциальный получатель предложения

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Данный сериализатор не должен изменять данные.")


class ChangeStatusExchangeProposalSerializer(serializers.ModelSerializer):
    """ Данный сериалайзер должен изменять столбец status(принимать или отклонять предложение обмена).
    А также обозначить предмет, который согласились предоставить в обмен,- столбец receiver_ad. """
    class Meta:
        model = ExchangeProposal
        fields = ("status",)
    status = serializers.CharField(required=True, max_length=1, validators=(check_exchange_item_status,))

    def create(self, validated_data):
        raise serializers.ValidationError("Данный сериализатор не должен создавать экземпляр записи в таблице ExchangeProposal ")

    def update(self, instance, validated_data):
        if instance.sender_ad.id == validated_data.receiver_ad.id:
            raise serializers.ValidationError(gettext("exchange_proposal_himself_error"))
