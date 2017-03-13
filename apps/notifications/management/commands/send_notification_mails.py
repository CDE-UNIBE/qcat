from django.core.management.base import NoArgsCommand

from notifications.models import Log


class Command(NoArgsCommand):
    """
    Send notification mails.
    """
    def handle_noargs(self, **options):
        logs = Log.objects.filter(was_sent=False)
        for log in logs:
            log.send_mails()
