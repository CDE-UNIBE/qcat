from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .conf import settings


def clean_wanted_actions(value):
    values = value.split(',')
    in_configuration = [int(value) in settings.NOTIFICATIONS_EMAIL_PREFERENCES for value in values]
    if not all(in_configuration):
        raise ValidationError(_('Invalid email status filters'))

