from django.db import models
from .conf import settings


class StatusQuerySet(models.QuerySet):
    """
    Helper for verbose queries. Use as:
    Questionnaire.with_status.published()
    """

    def public(self):
        return self.filter(status=settings.QUESTIONNAIRE_PUBLIC)

    def draft(self):
        return self.filter(status=settings.QUESTIONNAIRE_DRAFT)
