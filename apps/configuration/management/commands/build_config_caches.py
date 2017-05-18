from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils.translation import activate

from configuration.cache import get_configuration
from configuration.models import Configuration


class Command(NoArgsCommand):
    """
    This command creates all configuration caches for the current process.
    """
    def handle_noargs(self, **options):
        languages = dict(settings.LANGUAGES).keys()
        configurations = Configuration.objects.filter(active=True)
        for configuration in configurations:
            for language in languages:
                activate(language)
                get_configuration(configuration.code)
