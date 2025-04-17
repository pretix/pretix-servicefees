from django.db import models
from django.utils.translation import gettext_lazy as _


class ItemServicefeesSettings(models.Model):
    item = models.OneToOneField(
        "pretixbase.Item", related_name="servicefees_settings", on_delete=models.CASCADE
    )
    exclude = models.BooleanField(
        verbose_name=_(
            "Exclude this product from the calculation of per-ticket and percentual service fees"
        )
    )
