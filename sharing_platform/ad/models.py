import re
import uuid
from django.db import models
from django.utils.translation import gettext
from django.contrib.auth.models import User
from django.core.validators import ValidationError


ITEM_CONDITION = (
    ("n", gettext("select_state")),
    ("a", gettext("new")),
    ("b", gettext("used")),
)


EXCHANGE_PROPOSAL_STATUS = (
    ("s", gettext("success")),
    ("p", gettext("pending")),
    ("r", gettext("rejected"))
)


def status_item_validator(value):
    if value not in ("a", "b",):
        raise ValidationError(gettext("select_item_state"))


def exchange_item_validator(value):
    if value not in ("s", "p", "r",):
        raise ValidationError


def uuid_validator(val):
    if not re.match(re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"), val):
        raise ValidationError


class ArticleCategory(models.Model):
    """ Категория предмета """
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=150, blank=True)


class AdItem(models.Model):
    """ Предмет, участвующий в обмене """
    id = models.CharField(max_length=50, default=uuid.uuid4(), primary_key=True, validators=(uuid_validator,))
    name = models.CharField(blank=False, max_length=30, default="")
    description = models.CharField(max_length=150, blank=True, default="")
    image = ...
    category = models.ForeignKey(ArticleCategory, on_delete=models.SET_NULL, null=True)
    add_by = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    status = models.CharField(max_length=1, choices=ITEM_CONDITION, default="n", blank=False, validators=(status_item_validator,))


class ExchangeProposal(models.Model):
    """ Предложение бартерного обмена """
    id = models.CharField(max_length=50, default=uuid.uuid4(), primary_key=True, validators=(uuid_validator,))
    status = models.CharField(max_length=1, choices=EXCHANGE_PROPOSAL_STATUS, default="p", blank=False, validators=(exchange_item_validator,))
    sender_ad = models.ForeignKey(AdItem, on_delete=models.CASCADE, null=False, related_name="AdItem.id+")
    receiver_ad = models.ForeignKey(AdItem, blank=True, on_delete=models.CASCADE, null=True, default=None, related_name="AdItem.id+")
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.receiver_ad is not None:
            if self.sender_ad.id == self.receiver_ad.id:
                raise ValidationError(gettext("exchange_proposal_himself_error"))
        if self.__class__.objects.filter(id=self.id).exists():
            if self.status == "s" or self.status == "r":
                raise ValidationError("current_item_isnt_editable")  # Объявление, по которому состоялся обмен, или оно было отклонено, не подлежит редактированию.
        return super().clean()
