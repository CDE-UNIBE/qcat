from django.core.management.base import NoArgsCommand
from django.db import transaction

from notifications.models import Log


class Command(NoArgsCommand):
    """
    Send notification mails.
    """
    def handle_noargs(self, **options):

        with transaction.atomic():
            logs = Log.objects.select_for_update().filter(was_sent=False)

            for log in logs:
                log.send_mails()
                log.was_sent = True
                log.save()
