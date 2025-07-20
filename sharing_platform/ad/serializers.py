import uuid
import typing
from django.db.transaction import atomic
from django.utils.translation import gettext
from rest_framework import serializers
from .models import AdItem, ExchangeProposal


def check_exchange_item_status(value):
    if value not in ["s", "r"]:
        raise serializers.ValidationError


class AdItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdItem
        exclude = ("exchange",)

    def __init__(self, *a, request_user=None, **k):
        self.request_user = request_user
        super().__init__(*a, **k)
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=30, required=True, label=gettext("ad_item_name"))
    owner = serializers.HiddenField(default=None)

    def create(self, validated_data):
        user = getattr(self, "request_user", None)
        if user is None:
            raise ValueError
        validated_data.update({"owner": user})
        return super().create(validated_data)


class ExchangeInitListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdItem
        fields = "__all__"
    is_has_my_request = serializers.BooleanField(read_only=True)


class InitialExchangeProposalSerializer(serializers.ModelSerializer):
    """ Сериализатор инициализирущий предложение обмена. """
    class Meta:
        model = ExchangeProposal
        exclude = ("created_at",)

    def __init__(self, *a, request_user=None, sender=None, receiver=None, **k):
        self.request_user = request_user
        self._sender: typing.Optional[AdItem] = sender
        self._receiver: typing.Optional[AdItem] = receiver
        super().__init__(*a, **k)

    def validate(self, data):
        user = getattr(self, "request_user", None)
        if user is None:
            raise ValueError("Атрибут экземпляра 'request_user' необходимо передать для валидации")
        if not self._sender.owner.id == user.id:
            raise serializers.ValidationError(gettext("value_column_sender_ad_taken_current_user"))  # В качестве значения столбца sender_ad принимается предмет ПРЕДЛАГАЮЩЕГО пользователя (текущий request.user)
        if self._receiver.owner.id == user.id:
            raise serializers.ValidationError(gettext("value_column_receiver_ad_cnt_be_self_user"))  # В качестве значения receiver_ad должен выступать потенциальный получатель предложения
        return data

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Данный сериализатор не должен изменять данные.")

    def create(self, validated_data):
        ad_items = [self._sender, self._receiver]
        with atomic():
            new_exchange = ExchangeProposal(**validated_data)
            [ad_item.exchange.add(new_exchange) for ad_item in ad_items]
            new_exchange.save()
        return new_exchange


class ChangeStatusExchangeProposalSerializer(serializers.ModelSerializer):
    """ Данный сериалайзер должен изменять столбец status(принимать или отклонять предложение обмена).
    А также обозначить предмет, который согласились предоставить в обмен,- столбец receiver_ad. """
    class Meta:
        model = ExchangeProposal
        fields = ("status",)

    def create(self, validated_data):
        raise serializers.ValidationError("Данный сериализатор не должен создавать экземпляр записи в таблице ExchangeProposal ")


class OfferListSerializer(serializers.ModelSerializer):
    """ Сериализатор для вывода сдвоенных предметов в рамках их взаимоотношений обмена """
    class Meta:
        model = ExchangeProposal
        fields = "__all__"
    sender = AdItemSerializer(read_only=True)
    receiver = AdItemSerializer(read_only=True)
    receiver_is_request_user = serializers.BooleanField(read_only=True, default=False)
    sender_is_request_user = serializers.BooleanField(read_only=True, default=False)
    is_has_my_request = serializers.BooleanField(read_only=True, default=False)
    username_sender = serializers.CharField(read_only=True, default="")
    username_receiver = serializers.CharField(read_only=True, default="")
