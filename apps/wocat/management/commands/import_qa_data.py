from datetime import datetime

import petl
import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from wocat.management.commands.import_wocat_data import ImportObject, \
    WOCATImport, WOCAT_DATE_FORMAT, QCAT_DATE_FORMAT
from wocat.management.commands.qa_mapping import qa_mapping, custom_mapping_messages


# Characters used when merging multiple text entries into single (comments)
# field
TEXT_VALUES_MERGE_CHAR = '\n\n'

# Language mapping, mostly used to lookup translations (column named 'english')
# for Questionnaire with language code 'en'.
LANGUAGE_MAPPING = {
    'en': 'english',
    'es': 'spanish',
    'fr': 'french',
    'af': 'afrikaans',
    'ru': 'russian',
    'pt': 'portuguese',
}


class Command(BaseCommand):
    help = 'Imports the data from the old WOCAT QA database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--do-import',
            action='store_true',
            dest='do-import',
            default=False,
            help='Do the actual import.',
        )
        parser.add_argument(
            '--mapping-messages',
            action='store_true',
            dest='mapping-messages',
            default=False,
            help='Write a file which contains all mapping messages occuring '
                 'during the import.',
        )

    def handle(self, *args, **options):
        options['dry-run'] = options.get('do-import') is not True
        start_time = datetime.now()
        qa_import = QAImport(options)
        qa_import.collect_import_objects()
        qa_import.filter_import_objects()
        qa_import.check_translations()
        qa_import.do_mapping()
        qa_import.save_objects()
        end_time = datetime.now()
        print("End of import. Duration: {}.".format(end_time - start_time))


class QAImportObject(ImportObject):
    """
    Represents a QA object of the WOCAT database to be imported.
    """
    pass


class QAImport(WOCATImport):

    schema = 'qa'

    # Tables of the mapping are collected automatically.
    default_tables = [
        'approach',
        'qa_quality_review',
    ]
    lookup_table_name = 'qa_lookups'

    import_objects_exclude = []
    import_objects_filter = []

    # Attention: image_type column indicate what image it is
    # 1: Photo
    # 2: Flow chart
    # 3: Logo of institution
    file_info_table = 'qa_blob_info'

    image_url = 'https://qa.wocat.net/ThumbGenerate.php?id={}'

    questionnaire_identifier = 'approach_id'
    questionnaire_code = 'code'
    configuration_code = 'approaches'
    questionnaire_owner = 'main_contributor'

    default_compiler_id = 3726

    mapping = qa_mapping
    custom_mapping_messages = custom_mapping_messages

    def __init__(self, command_options):

        super().__init__(command_options)

        # LOCAL
        # self.connection = psycopg2.connect(
        #     settings.WOCAT_IMPORT_DATABASE_URL_LOCAL)

        # REMOTE (productive)
        self.connection = psycopg2.connect(
            settings.WOCAT_IMPORT_DATABASE_URL)


    def collect_import_objects(self):
        """
        Query and put together all QA objects which will be imported.
        """

        def get_tables(mappings):
            """
            Recursively collect all WOCAT tables of the mappings.

            Args:
                mappings: list.

            Returns:
                list. A list of tables.
            """
            tables = []
            for mapping in mappings:
                table = mapping.get('wocat_table')
                if table:
                    tables.append(table)
                tables.extend(get_tables(mapping.get('mapping', [])))
                tables.extend(get_tables(mapping.get('conditions', [])))
            return tables

        self.output('Fetching data from WOCAT QA database.', v=1)

        # Extend the default tables by adding the ones from the mapping.
        tables = self.default_tables
        for qg_properties in self.mapping.values():
            questions = qg_properties.get('questions', {})
            for q_properties in questions.values():
                tables.extend(get_tables(q_properties.get('mapping', [])))

        # Remove duplicates
        tables = list(set(tables))

        # Try to query the lookup table and collect its values.
        try:
            lookup_query = """
                    SELECT *
                    FROM {schema}.{table_name};
                """.format(schema=self.schema,
                           table_name=self.lookup_table_name)
            lookup_table = {}
            for row in petl.dicts(petl.fromdb(self.connection, lookup_query)):
                lookup_table[row.get('id')] = row
        except AttributeError:
            lookup_table = {}

        # So far, lookup_text is never used. Therefore it can be left empty.
        lookup_table_text = {}

        # Try to query file infos
        try:
            lookup_query_files = """
                    SELECT *
                    FROM {schema}.{table_name};
                """.format(schema=self.schema,
                           table_name=self.file_info_table)
            file_infos = {}
            for row in petl.dicts(
                    petl.fromdb(self.connection, lookup_query_files)):
                file_infos[row.get('blob_id')] = row
        except AttributeError:
            file_infos = {}

        for table_name in tables:
            query = 'SELECT {columns} FROM {schema}.{table_name};'.format(
                columns='*', schema=self.schema, table_name=table_name)

            queried_table = petl.fromdb(self.connection, query)
            row_errors = False
            for row in petl.dicts(queried_table):

                if row_errors is True:
                    continue

                # Inconsistent naming throughout the tables
                questionnaire_identifier = self.questionnaire_identifier
                if table_name == 'approach':
                    questionnaire_identifier = 'id'
                elif table_name == 'qa_quality_review':
                    questionnaire_identifier = 'qa_id'

                identifier = row.get(questionnaire_identifier)
                if identifier is None:
                    self.output('No identifier found for table "{}".'.format(
                        table_name), v=1, l='error')
                    row_errors = True

                if identifier in self.import_objects_exclude:
                    continue

                import_object = self.get_import_object(identifier)

                if import_object is None:
                    import_object = QAImportObject(
                        identifier, self.command_options, lookup_table,
                        lookup_table_text, file_infos, self.image_url)

                    import_object.add_custom_mapping_messages(
                        self.custom_mapping_messages)

                    self.import_objects.append(import_object)

                # Set the code if it is available in the current table
                code = row.get(self.questionnaire_code)
                if code:
                    import_object.set_code(code)

                # The main contributor is the compiler
                compiler_id = row.get(self.questionnaire_owner)

                if compiler_id:
                    # If the main contributer is "Not registered" (ID 661), use
                    # the default compiler
                    if compiler_id == 661:
                        compiler_id = self.default_compiler_id
                        import_object.add_mapping_message(
                            'Using "Unknown User" as compiler in QCAT as main '
                            'contributor in QA was "Not registered"')

                    # TODO: This is a temporary fix for invalid user IDs
                    elif identifier in [131, 128, 89, 47, 106, 82, 195, 212,
                                        76, 107, 84, 139, 130, 276, 72, 147,
                                        138, 43, 44, 46, 49, 50, 52, 57, 173,
                                        171, 170, 166, 125, 78, 102, 45, 197,
                                        48]:

                        compiler_id = self.default_compiler_id

                    import_object.set_owner(compiler_id)

                # Use the creation date available on the approach table
                created = row.get('date')
                if created and table_name == 'approach':
                    creation_time = datetime.strptime(
                        created, WOCAT_DATE_FORMAT)
                    import_object.created = timezone.make_aware(
                        creation_time, timezone.get_current_timezone())

                import_object.add_wocat_data(table_name, row)

    def filter_import_objects(self):
        """
        Filter the import objects based on status and custom filters.

        Returns:
            -
        """
        # Filter out all questionnaires which have not code (and therefore no
        # created_date etc.)
        self.import_objects = [
            io for io in self.import_objects if io.code != '']

        # Custom filter
        if self.import_objects_filter:
            import_objects = []
            for filter_identifier in self.import_objects_filter:
                import_object = self.get_import_object(filter_identifier)
                if import_object:
                    import_objects.append(import_object)
            self.import_objects = import_objects

        self.output('{} objects remained after filtering.'.format(
            len(self.import_objects)), v=1)
