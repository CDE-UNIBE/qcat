# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .errors import QuestionnaireLockedException
from .models import Questionnaire


@receiver(pre_save, sender=Questionnaire)
def prevent_updates_on_published_items(instance, *args, **kwargs):
    if instance.id:
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
        has_blocked_version = Questionnaire.objects.exclude(
            id=instance.id
        ).filter(
            code=instance.code,
            blocked__isnull=False
        )
        if instance.blocked:
            has_blocked_version = has_blocked_version.exclude(
                blocked=instance.blocked
            )
        if has_blocked_version.exists():
            raise QuestionnaireLockedException(
                has_blocked_version.first().blocked
            )
