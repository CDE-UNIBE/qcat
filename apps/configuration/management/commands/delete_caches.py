from django.core.management.base import NoArgsCommand

from configuration.cache import delete_configuration_cache
from configuration.models import Configuration


class Command(NoArgsCommand):
    """
    This command deletes all configuration caches.
    """
    def handle_noargs(self, **options):
        active_configurations = Configuration.objects.filter(active=True)
        for configuration in active_configurations:
            delete_configuration_cache(configuration)
