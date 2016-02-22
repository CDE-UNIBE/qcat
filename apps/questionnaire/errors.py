# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _


class QuestionnaireException(Exception):
    """
    Base class for all exceptoins regarding the questionnaire.
    """
    pass


class QuestionnaireLockedException(QuestionnaireException):
    """
    A questionnaire can be edited by only one concurrent user.
    """
    def __init__(self, user):
        self.user = user

    def __str__(self):
        message = _(u"This questionnaire is locked for editing by {}")
        return repr(message.format(self.user))
