# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .errors import QuestionnaireLockedException
from .models import Questionnaire, Lock
from .conf import settings


@receiver(pre_save, sender=Questionnaire)
def prevent_updates_on_published_items(instance, *args, **kwargs):
    if instance.id and instance.status != settings.QUESTIONNAIRE_INACTIVE:
        qs = Questionnaire.objects.filter(id=instance.id, status=4)
        if qs.exists():
            raise ValidationError(
                _(u"Published questionnaires must not be updated.")
            )


@receiver(pre_save, sender=Questionnaire)
def prevent_editing_of_locked_questionnaires(instance, *args, **kwargs):
    """
    Make sure that no other questionnaire with the same code is blocked.

    Args:
        instance: Questionnaire
    """
    if instance.id:
        locks = Lock.with_status.is_blocked(code=instance.code)
        if locks.exists():
            raise QuestionnaireLockedException(
                locks.first().user
            )
