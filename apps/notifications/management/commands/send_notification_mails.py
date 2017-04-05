import logging

from django.core.management.base import NoArgsCommand
from django.utils.timezone import now

from notifications.models import Log

logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    """
    Send notification mails.
    """
    def handle_noargs(self, **options):
        logs = Log.objects.filter(was_processed=False)
        for log in self.logged_generator(logs):
            log.send_mails()

    @staticmethod
    def logged_generator(logs):
        """
        Log start of loop, each step, and end.
        """
        logger.info('{date}: start sending {count} mails'.format(
            date=now(), count=logs.count()
        ))
        for log in logs:
            yield log
            logger.info('{date}: sent log {id}'.format(
                date=now(), id=log.pk
            ))
        logger.info('{date}: finished sending mails'.format(date=now()))
