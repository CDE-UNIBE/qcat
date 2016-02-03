# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from questionnaire.models import Questionnaire


@receiver(pre_save, sender=Questionnaire)
def prevent_updates_on_published_items(instance, *args, **kwargs):
    if instance.id:
        qs = Questionnaire.objects.filter(id=instance.id, status=4)
        if qs.exists():
            raise ValidationError(
                _(u"Published questionnaires must not be updated.")
            )
