from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils.translation import activate

from configuration.cache import get_configuration
from configuration.models import Configuration
from ...index import get_mappings, create_or_update_index


class Command(NoArgsCommand):
    """
    This command creates elasticsearch indexes for all available
    questionnaires. This is primarily used for running tests on shippable.
    """
    def handle_noargs(self, **options):
        """
        Loop over all active configurations, get the mappings and create the
        elasticsearch-indexes.

        Args:
            **options: None

        """
        configurations = Configuration.objects.filter(active=True)
        for language in dict(settings.LANGUAGES).keys():
            activate(language)
            for configuration in configurations:
                questionnaire_configuration = get_configuration(
                    configuration.code
                )
                mappings = get_mappings(questionnaire_configuration)
                create_or_update_index(configuration.code, mappings)
