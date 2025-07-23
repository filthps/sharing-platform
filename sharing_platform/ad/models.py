import re
import uuid
from django.db import models
from django.utils.translation import gettext
from django.contrib.auth.models import User
from django.core.validators import ValidationError
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill


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
        raise ValidationError(gettext("select_state"))


def exchange_item_validator(value):
    if value not in ("s", "p", "r",):
        raise ValidationError


def uuid_validator(val):
    if not re.match(re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"), val):
        raise ValidationError


class ArticleCategory(models.Model):
    """ Категория предмета """
    name = models.CharField(max_length=50, blank=False, unique=True)
    description = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name


class AdItem(models.Model):
    """ Предмет, участвующий в обмене """
    id = models.CharField(max_length=50, default=uuid.uuid4, primary_key=True, validators=(uuid_validator,))
    name = models.CharField(blank=False, max_length=50, default="", verbose_name=gettext("ad_item_name"))
    description = models.CharField(max_length=150, blank=True, default="", verbose_name=gettext("ad_item_description"))
    image = models.ImageField(upload_to="images", blank=True, null=True, default=None, verbose_name=gettext("ad_item_image"))
    list_thumb = ImageSpecField(source='image',
                                processors=[ResizeToFill(100, 50)],
                                format='JPEG',
                                options={'quality': 60})
    preview_thumb = ImageSpecField(source='image',
                                   processors=[ResizeToFill(200, 100)],
                                   format='JPEG',
                                   options={'quality': 80})
    mini_thumb = ImageSpecField(source='image',
                                processors=[ResizeToFill(20, 20)],
                                format='JPEG',
                                options={'quality': 30})
    category = models.ForeignKey(ArticleCategory, on_delete=models.PROTECT, blank=False, verbose_name=gettext("ad_item_category"))
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, verbose_name=gettext("ad_item_owner"))
    status = models.CharField(max_length=1, choices=ITEM_CONDITION, default="n", blank=False,
                              validators=(status_item_validator,), verbose_name=gettext("ad_item_quality_status"))
    exchange = models.ManyToManyField("ExchangeProposal", blank=True, null=True, related_name="id+")

    def __str__(self):
        return self.name


class ExchangeProposal(models.Model):
    """ Предложение бартерного обмена.
     Текущий хозяин вещи - 'sender_ad'  """
    id = models.CharField(max_length=50, default=uuid.uuid4, primary_key=True, validators=(uuid_validator,))
    status = models.CharField(max_length=1, choices=EXCHANGE_PROPOSAL_STATUS, default="p", blank=False, validators=(exchange_item_validator,), verbose_name=gettext("exchange_status"))
    sender = models.ForeignKey(AdItem, blank=False, on_delete=models.CASCADE, related_name="AdItem.id+", verbose_name=gettext("sender"))  # Текущий держатель вещи (инициатор заявки)
    receiver = models.ForeignKey(AdItem, blank=False, on_delete=models.CASCADE, related_name="AdItem.id+", verbose_name=gettext("receiver"))  # Потенциальный получатель(новый хозяин), который должен одобрить обмен
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=gettext("created_at"))

    def clean(self):
        if self.sender.id == self.receiver.id:
            raise ValidationError(gettext("exchange_proposal_himself_error"))  # Нельзя обменивать предмет самого на себя
        if self.sender.owner.id == self.receiver.owner.id:
            raise ValidationError(gettext("offer_exchange_yourself_error"))  # Нельзя обмениваться своими собственными предметами самому с собой ИМХО
        if self.__class__.objects.filter(id=self.id).count():
            if self.status == "s" or self.status == "r":
                raise ValidationError("current_item_isnt_editable")  # Совершённая сделка не подлежит редактированию.
        return super().clean()

    def __str__(self):
        return f"{self.sender.name } --> {self.receiver.name}"
