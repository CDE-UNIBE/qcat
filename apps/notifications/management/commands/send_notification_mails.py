from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    """
    Purge stale locks.
    """
    def handle_noargs(self, **options):
        # check unsent logs.

        # collect subscribers

        # filter according to preferences

        # send
        pass
