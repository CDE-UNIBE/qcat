from datetime import timedelta
from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.db.models import Q
from django.utils.timezone import now
from questionnaire.models import Lock


class Command(NoArgsCommand):
    """
    Purge stale locks.
    """
    def handle_noargs(self, **options):
        expired = now() - timedelta(minutes=settings.QUESTIONNAIRE_LOCK_TIME)
        Lock.objects.filter(
            Q(is_finished=True) | Q(start__lte=expired)
        ).delete()
