from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver

from accounts.models import User
from questionnaire.models import Questionnaire
from questionnaire import signals

from .utils import ContentLog, MemberLog, StatusLog


@receiver(signals.change_status)
def create_status_notification(sender: int, questionnaire: Questionnaire, user: User, **kwargs):
    StatusLog(
        action=sender, sender=user, questionnaire=questionnaire, **kwargs
    ).create(
        is_rejected=kwargs.get('is_rejected', False),
        message=kwargs.get('message', '')

    )


@receiver(signals.change_member)
def modify_member(sender: int, questionnaire: Questionnaire, user: User, affected: User, role: str, **kwargs):
    MemberLog(
        action=sender, sender=user, questionnaire=questionnaire, **kwargs
    ).create(
        affected=affected, role=role
    )


@receiver(signals.create_questionnaire)
def create_questionnaire(sender: int, questionnaire: Questionnaire, user: User, **kwargs):
    StatusLog(
        action=sender, sender=user, questionnaire=questionnaire, **kwargs
    ).create(
        is_rejected=False,
        message=_('Created')
    )


@receiver(signals.delete_questionnaire)
def delete_questionnaire(sender: int, questionnaire: Questionnaire, user: User, **kwargs):
    StatusLog(
        action=sender, sender=user, questionnaire=questionnaire, **kwargs
    ).create(
        is_rejected=False,
        message=_('Deleted')
    )


@receiver(signals.change_questionnaire_data)
def change_questionnaire_data(sender: int, questionnaire: Questionnaire, user: User, **kwargs):
    ContentLog(action=sender, sender=user, questionnaire=questionnaire, **kwargs).create()
