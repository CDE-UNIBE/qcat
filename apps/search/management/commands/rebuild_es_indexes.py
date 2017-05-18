from django.core.management import call_command
from django.core.management.base import NoArgsCommand

from search.index import delete_all_indices, put_all_data


class Command(NoArgsCommand):
    """
    Delete, recreate and fill all indexes.
    """
    def handle_noargs(self, **options):
        delete_all_indices()
        call_command('create_es_indexes')
        put_all_data()
