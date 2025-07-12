import uuid
from django.db import models
from django.utils.translation import gettext
from django.contrib.auth.models import User
from django.core.validators import ValidationError


ITEM_CONDITION = (
    ("n", gettext("select_state")),
    ("a", gettext("new")),
    ("b", gettext("used")),
    ("c", gettext("very_worn_item"))
)


def status_item_validator(value):
    if value == "n":
        raise ValidationError(gettext("select_item_state"))


class ArticleCategory(models.Model):
    """ Категория предмета """
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=150, blank=True)


class Article(models.Model):
    """ Предмет, участвующий в обмене """
    id = models.CharField(default=uuid.uuid4(), primary_key=True)
    description = models.CharField(max_length=150, blank=False, default="")
    image = ...
    category = models.ForeignKey(ArticleCategory, on_delete=models.PROTECT)
    add_by = models.ForeignKey(User, null=False, on_delete=models.PROTECT)
    status = models.CharField(choices=ITEM_CONDITION, default="n", blank=False, validators=(status_item_validator,))


class ExchangeProposal(models.Model):
    """ Предложение бартерного обмена """
    id = models.CharField(default=uuid.uuid4(), primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.PROTECT)
    receiver = models.ForeignKey(User, on_delete=models.PROTECT)

    def clean(self):
        if self.sender.id == self.receiver.id:
            raise ValidationError("exchange_proposal_himself")
        return super().clean()

