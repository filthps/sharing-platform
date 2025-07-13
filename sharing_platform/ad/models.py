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
    if value == "n":
        raise ValidationError(gettext("select_item_state"))


class ArticleCategory(models.Model):
    """ Категория предмета """
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=150, blank=True)


class Article(models.Model):
    """ Предмет, участвующий в обмене """
    id = models.CharField(default=uuid.uuid4(), primary_key=True)
    name = models.CharField(blank=False, max_length=30, default="")
    description = models.CharField(max_length=150, blank=True, default="")
    image = ...
    category = models.ForeignKey(ArticleCategory, on_delete=models.PROTECT)
    add_by = models.ForeignKey(User, null=False, on_delete=models.PROTECT)
    status = models.CharField(choices=ITEM_CONDITION, default="n", blank=False, validators=(status_item_validator,))


class ExchangeProposal(models.Model):
    """ Предложение бартерного обмена """
    id = models.CharField(default=uuid.uuid4(), primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE)
    given_item = models.ForeignKey(Article, on_delete=models.CASCADE)
    received_item = models.ForeignKey(Article, on_delete=models.CASCADE)
    status = models.CharField(choices=EXCHANGE_PROPOSAL_STATUS, default="p", blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.sender.id == self.receiver.id:
            raise ValidationError(gettext("exchange_proposal_himself_error"))
        if self.given_item.id == self.received_item.id:
            raise ValidationError(gettext("article_match_error"))
        return super().clean()
