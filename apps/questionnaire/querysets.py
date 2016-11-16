import operator
from datetime import timedelta
from functools import reduce

from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from .conf import settings


class StatusQuerySet(models.QuerySet):
    """
    Helper for verbose queries. Use as: Questionnaire.with_status.published()
    """

    def public(self):
        return self.filter(status=settings.QUESTIONNAIRE_PUBLIC)

    def draft(self):
        return self.filter(status=settings.QUESTIONNAIRE_DRAFT)

    def not_deleted(self):
        return self.filter(is_deleted=False)


class LockStatusQuerySet(models.QuerySet):
    """
    Helpers to get locked / unlocked Questionnaires
    """

    @property
    def expired(self):
        # Latest time in which locks are valid
        return now() - timedelta(minutes=settings.QUESTIONNAIRE_LOCK_TIME)

    def filter_code(self, code: str):
        return self.filter(questionnaire_code=code)

    def is_blocked(self, code: str, for_user=None):
        """
        Filters locks that are active
        """
        qs = self.filter_code(code=code).filter(
            is_finished=False, start__gte=self.expired
        )
        if for_user:
            qs = qs.exclude(user=for_user)
        return qs

    def is_editable(self, code: str, for_user=None):
        """

        """
        filters = Q(is_finished=True) | Q(start__lte=self.expired)
        if for_user:
            filters |= Q(user=for_user)

        return self.filter_code(code=code).filter(filters)
