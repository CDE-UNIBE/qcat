from collections import OrderedDict

import re
from datetime import datetime
import json
import pprint
import psycopg2
import petl as etl
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.management import color_style
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.translation import activate

from accounts.client import typo3_client
from accounts.models import User
from configuration.cache import get_configuration
from notifications.receivers import create_questionnaire
from questionnaire import signals
from questionnaire.models import Questionnaire, File
from questionnaire.utils import clean_questionnaire_data
from wocat.management.commands.qt_mapping import qt_mapping, \
    custom_mapping_messages

pp = pprint.PrettyPrinter(indent=2)


# Date format used in WOCAT database: 2010-04-20
WOCAT_DATE_FORMAT = '%Y-%m-%d'

# Date format expected by QCAT: 20/04/2010
QCAT_DATE_FORMAT = '%d/%m/%Y'

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
    'fa': 'dari',
    'pt': 'portuguese',

    # Languages with lookup values but no QT Questionnaire is available in this
    # language.
    'mn': 'mongolian',
    'tg': 'tajik',
    'el': 'greek',
}

FILE_CONTENT_MAPPING = {
    'image/pjpeg': 'image/jpeg',
    'image/x-png': 'image/png',
}

MAPPING_MESSAGES_FILENAME = 'wocat_import_mapping_messages.txt'


def sort_by_key(entry, key, none_value=0):
    """
    Helper function to sort a dictionary by a given key.

    Args:
        entry: dict.
        key: str.
        none_value: int. The default value to be used if the key is not present
            in the dict.
    """
    v = entry.get(key)
    if not v:
        return none_value
    return v


class Command(BaseCommand):
    help = 'Imports the data from the old WOCAT database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry-run',
            default=False,
            help='Only extract and transform the data, do not import anything.',
        )
        parser.add_argument(
            '--error-list',
            action='store_true',
            dest='error-list',
            default=False,
            help='Print a list of questionnaires which contain errors.',
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
        start_time = datetime.now()
        qt_import = QTImport(options)
        qt_import.collect_import_objects()
        qt_import.filter_import_objects()
        qt_import.check_translations()
        qt_import.do_mapping()
        qt_import.save_objects()
        end_time = datetime.now()
        print("End of import. Duration: {}.".format(end_time - start_time))


class Logger:
    """
    A mixin used to log output.
    """
    command_options = {}
    style = color_style()

    def output(self, msg, v=None, l=None, pretty=False):
        """
        Print output.

        Args:
            msg: The message to be printed.
            v: Verbosity level (1 - 3)
            l: Level of the output, used to format the output. Use one of
                'error', 'warning' or 'success' to apply styling.
            pretty: Set to true to prettify output.

        Returns:
            -
        """
        if l == 'error':
            msg = self.style.NOTICE(msg)
        elif l == 'warning':
            msg = self.style.WARNING(msg)
        elif l == 'success':
            msg = self.style.SQL_COLTYPE(msg)
        if not v or v <= self.command_options['verbosity']:
            if pretty is True:
                pp.pprint(msg)
            else:
                print(msg)


class ImportObject(Logger):
    """
    Represents an object of the WOCAT database to be imported.
    """

    def __init__(
            self, identifier, command_options, lookup_table, lookup_table_text,
            file_infos, image_url):
        self.identifier = identifier
        self.command_options = command_options
        self.lookup_table = lookup_table
        self.lookup_table_text = lookup_table_text
        self.file_infos = file_infos
        self.image_url = image_url

        # Data will be stored as
        # {
        #   "table_name": [
        #       { _table_content_ }
        #   ]
        # }
        self.wocat_data = {}

        self.data_json = {}
        self.data_json_cleaned = {}

        # These values will be set/overwritten after reading the data.
        self.created = None
        self.code_wocat = ''
        self.code = ''
        self.language = 'en'
        self.questionnaire_owner = None

        # A list of ImportObjects which are translations of the current object.
        self.translations = []

        # Error messages
        self.mapping_errors = []
        self.validation_errors = []

        # Mapping messages: Informs about special procedures which took place
        # during mapping of the data.
        self.mapping_messages = []

        # The QCAT questionnaire object once it is created.
        self.questionnaire_object = None

    def __str__(self):
        return '[{} | {}]'.format(self.identifier, self.code_wocat)

    def set_code(self, code_wocat):
        """
        Set the WOCAT code of the current Questionnaire. Also extract the base
        code and the language of the Questionnaire.

        Args:
            code_wocat: The WOCAT code in the form of T_MOR010en.

        Returns:
            -
        """
        self.code_wocat = code_wocat

        # Assumption: Code always of form
        # [Type]_[COUNTRY][3 Integers][LANGUAGE]
        # Example:
        # T_MOR010en
        code_parts = re.findall('[a-zA-Z_]+\d{3}', self.code_wocat)
        if not len(code_parts) == 1:
            raise Exception('Invalid code: {}'.format(self.code_wocat))
        code = code_parts[0]
        self.code = code

        language = self.code_wocat.replace(code, '')
        if language not in LANGUAGE_MAPPING:
            raise Exception('Invalid language code: {}'.format(self.code_wocat))
        self.language = language

    def set_owner(self, user_id):
        """
        Set the owner of the current import object. If the user does not yet
        exist in the local database, its user details are queried through the
        typo3 client and a new user is created.

        Args:
            user_id: The ID of the user.

        Returns:
            -
        """
        dry_run = self.command_options['dry-run']
        if dry_run:
            return

        # Yes, this is a very ugly shortcut to deal with duplicate email entries
        # in the (fortunately soon obsolete) user database.
        if user_id == 165:
            user_id = 551

        try:
            # Check if user already exists in the DB
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            # If User does not exist, create and update it.
            user_info = typo3_client.get_user_information(user_id)

            if not user_info:
                self.add_error(
                    'validation', 'User with ID {} does not exist.'.format(
                        user_id))
                return

            user, created = User.objects.get_or_create(pk=user_info['uid'])
            typo3_client.update_user(user, user_info)

        self.questionnaire_owner = user

    def add_error(self, error_type, error_msg):
        if error_type == 'mapping':
            self.mapping_errors.append(error_msg)
        elif error_type == 'validation':
            self.validation_errors.append(error_msg)
        else:
            raise NotImplementedError('Error type {} not supported.'.format(
                error_type))

    def print_errors(self):
        self.output('\nErrors for object {}:\n'.format(self))

        if self.mapping_errors:
            self.output('Mapping errors:')
        for error in self.mapping_errors:
            self.output(error)

        if self.validation_errors:
            self.output('Validation errors:')
        for error in self.validation_errors:
            self.output(error)

    def get_error_count(self):
        return len(self.mapping_errors) + len(self.validation_errors)

    def has_errors(self):
        return self.get_error_count() > 0

    def add_wocat_data(self, table_name, new_table_data):
        """
        Add data from a WOCAT table to the internal collection of WOCAT data.

        # Data will be stored as
        # {
        #   "table_name": [
        #       { _table_content_ }
        #   ]
        # }

        Args:
            table_name: The name of the WOCAT table.
            new_table_data: A dictionary to be added to the table_content list.

        Returns:
            -
        """
        table_data = self.get_wocat_table_data(table_name)
        if table_data is None:
            table_data = []
        table_data.append(new_table_data)
        self.wocat_data[table_name] = table_data

    def get_wocat_table_data(self, table_name):
        return self.wocat_data.get(table_name)

    def get_wocat_attribute_data(self, table_name, attribute_name):
        """
        Return a list of attributes found in the WOCAT data.

        Args:
            table_name: The WOCAT table name.
            attribute_name: The WOCAT attribute name (the table column).

        Returns:
            list. A list of attributes.
        """
        wocat_table_data = self.get_wocat_table_data(table_name)
        if wocat_table_data is None:
            return []
        attribute_data = []
        for wocat_table_d in wocat_table_data:
            attribute_d = wocat_table_d.get(attribute_name)
            if attribute_d:
                attribute_data.append(attribute_d)
        return attribute_data

    def check(self, configuration):
        """
        Clean and check the data (data_json) against the configuration. If it
        is valid, save the cleaned data json (data_json_cleaned). Else collect
        the error messages.

        Args:
            configuration: The name of the current configuration.

        Returns:
            -
        """
        # Update (20.12.2016): It was decided to temporarily increase the
        # max_length limit of the description
        cleaned_data, errors = clean_questionnaire_data(
            self.data_json, configuration, no_limit_check=False)

        for error in errors:
            self.add_error('validation', error)

        if errors:
            return

        # Since max_length is ignored, add at least a mapping message that the
        # text was too long
        __, errors_text_limit = clean_questionnaire_data(
            self.data_json, configuration, no_limit_check=False)
        for error in errors_text_limit:
            self.add_mapping_message(
                'Ignoring max_length error: {}'.format(error))

        self.data_json_cleaned = cleaned_data

    def save(self, configuration):
        """
        Actually insert the object in the QCAT database.

        Args:
            configuration: The name of the current configuration.

        Returns:
            -
        """
        # First language is always the original
        languages = [self.language]
        for translation in self.translations:
            languages.append(translation.language)
        self.output('Saving object {}'.format(self), v=2)
        questionnaire = Questionnaire.create_new(
            configuration_code=configuration.configuration_keyword,
            data=self.data_json, user=self.questionnaire_owner,
            previous_version=None, status=2, created=self.created,
            old_data=None, languages=languages)
        questionnaire.update_geometry(configuration.configuration_keyword)
        return questionnaire

    def handle_file(self, file_id):

        try:
            file_id = int(file_id)
        except ValueError:
            return None

        if file_id in [
            902,
            1014,
            1515,
            3202,
        ]:
            self.add_mapping_message('File {} not found.'.format(file_id))
            return None

        if file_id in [
            4752, 886, 1309,
        ]:
            self.add_mapping_message(
                'There was a problem with the file {}.'.format(file_id))
            return None

        file_info = self.file_infos.get(int(file_id))
        if file_info is None:
            self.add_error(
                'mapping', 'No file info found with ID {} for object {}'.format(
                    file_id, self))

        content_type = file_info.get('blob_content_type')
        mapped_content_type = FILE_CONTENT_MAPPING.get(
            content_type, content_type)

        if mapped_content_type in [
            'image/jpeg',
            'image/gif',
            'image/png',
                ]:
            # Image
            url = self.image_url.format(file_id)

            dry_run = self.command_options['dry-run']
            if dry_run:
                return None

            self.output(
                'Processing file {} for object {}'.format(file_id, self), v=2)

            response = requests.get(url)
            file = ContentFile(response.content)
            uploaded_file = UploadedFile(
                file=file, content_type=mapped_content_type, size=file.size)
            file_object = File.handle_upload(uploaded_file)

            return file_object.uuid

        else:
            self.add_error('mapping', 'Unsupported content type: {}'.format(
                mapped_content_type))

    def add_custom_mapping_messages(self, custom_messages):
        for custom_mapping_message in custom_messages:
            if self.identifier in custom_mapping_message.get('ids', []):
                self.add_mapping_message(custom_mapping_message.get('message'))

    def add_mapping_message(self, message):
        if message and message not in self.mapping_messages:
            self.mapping_messages.append(message)

    def get_mapping_messages(self):
        return sorted(self.mapping_messages)

    def apply_index_filter(self, values, index_filter):
        index_values = self.collect_mapping(
            index_filter.get('mapping'), return_list=True)

        value = index_filter.get('value')
        operator = index_filter.get('operator')

        if operator == 'equals':
            indices = [i for i, x in enumerate(index_values) if x == value]
        else:
            raise NotImplementedError(
                'Operator {} is not valid as an index filter'.format(operator))

        return [values[i] for i in indices]

    def check_conditions(
            self, conditions, condition_message, condition_message_opposite,
            conditions_join):
        """
        Check conditions defined in the mapping.

        Args:
            conditions: A list of condition dicts. Each condition must contain
                - mapping
                - operator (contains / contains_not, len_gte, ...)
                - value
            condition_message: The message to be added if the condition is true.
            condition_message_opposite: The message to be added if the condition
                is false!
            conditions_join: An operator declaring how to join multiple
                conditions. Use 'and' (all conditions must be true) or 'or'
                ([default] - only one condition must be true).

        Returns:
            Boolean.
        """

        def evaluate_condition(operator, cond_value, ref_value):
            """
            Evaluate a condition.

            Args:
                operator: The operator of the evaluation, eg. "contains".
                cond_value: The value used for the condition. Usually a single
                    value.
                ref_value: The value used as reference. Usually a list.

            Returns:
                bool.
            """
            if operator == 'contains':
                return cond_value in ref_value
            elif operator == 'contains_not':
                return cond_value not in ref_value
            elif operator == 'len_lte':
                return len(ref_value) <= int(cond_value)
            elif operator == 'len_gte':
                return len(ref_value) >= int(cond_value)
            elif operator == 'is_empty':
                return len(ref_value) == 0
            elif operator == 'not_empty':
                return len(ref_value) != 0
            elif operator == 'one_of':
                if isinstance(ref_value, list):
                    if len(ref_value) == 0:
                        return False
                    elif len(ref_value) > 1:
                        raise Exception(
                            'List for one_of ({}) should contain exactly 1 '
                            'element.'.format(ref_value))
                    ref_value = ref_value[0]
                return ref_value in cond_value
            else:
                raise NotImplementedError(
                    'Condition operator "{}" not specified or not valid'.format(
                        operator))

        evaluated = []

        for condition in conditions:
            condition_operator = condition.get('operator')

            return_row_values = False
            if condition_operator == 'custom':
                return_row_values = True

            condition_values = self.collect_mapping(
                mappings=condition.get('mapping', []), return_list=True,
                return_row_values=return_row_values)

            # Actually check the condition
            condition_value = condition.get('value')

            if condition_operator != 'custom':
                evaluated.append(evaluate_condition(
                    condition_operator, condition_value, condition_values))

            else:
                # Custom evaluation
                custom_evaluated = []
                custom_conditions = condition.get('custom', [])
                if not custom_conditions:
                    raise Exception('No "custom" directive indicated.')

                for condition_value in condition_values:

                    row_evaluated = []
                    for custom_condition in custom_conditions:
                        custom_operator = custom_condition.get('operator')
                        custom_key = custom_condition.get('key')
                        custom_value = custom_condition.get('value')

                        row_evaluated.append(evaluate_condition(
                            custom_operator, custom_value,
                            condition_value.get(custom_key)))

                    # All conditions for one row must be True.
                    custom_evaluated.append(all(row_evaluated))

                # Any custom evaluated row needs to be true.
                evaluated.append(any(custom_evaluated))

        if conditions_join == 'and':
            conditions_fulfilled = all(evaluated)
        else:
            conditions_fulfilled = any(evaluated)

        if conditions_fulfilled is True:
            self.add_mapping_message(condition_message)
        else:
            self.add_mapping_message(condition_message_opposite)

        return conditions_fulfilled

    def collect_mapping(
            self, mappings, separator=None, value_mapping_list=None,
            return_list=False, value_prefix='', value_suffix='',
            return_row_values=False, no_duplicates=False, table_data=None):
        """
        Collect the values defined in the mapping.

        Args:
            mappings: A list of mapping dicts. Each mapping must contain
                - wocat_table: The name of the WOCAT table
                - wocat_column: The name of the WOCAT table column.
                - mapping_prefix (optional): A prefix to be added to each value.
                - mapping_suffix (optional): A suffix to be added to each value.
                - conditions (optional): A list of conditions.
            separator: A separator to be used if multiple values are joined (if
                not specified, the default is used).
            value_mapping_list: A dict of values to be used for the mapping.
            return_list: Boolean. Returns the values as list if true.
            value_prefix: A prefix to be added to the final value.
            value_suffix: A suffix to be added to the final value.
            return_row_values: Return the entire row values of the mapping (
                wocat_column is not respected). It is returned as list of dicts.
            no_duplicates: Boolean. Whether to remove duplicates from values
                list or not.
            table_data: Dict. Optionally already provide a dictionary of WOCAT
                table data. In this case, the mapping needs only the
                wocat_column entries to access the values from the dict.

        Returns:
            String. (or list if return_list=True)
        """

        def do_value_mapping(v):
            """
            Helper function to do the mapping of a value, such as adding prefix
            and suffix, look up values etc.

            Args:
                v: -

            Returns:
                string.
            """
            value_mapping = mapping.get('value_mapping')
            if value_mapping:
                v = value_mapping

            v = '{}{}{}'.format(
                mapping.get('mapping_prefix', ''),
                v,
                mapping.get('mapping_suffix', ''))

            if value_mapping_list:
                try:
                    v = value_mapping_list.get(int(v), v)
                except ValueError:
                    v = value_mapping_list.get(v, v)

            lookup_table = mapping.get('lookup_table')
            lookup_text = mapping.get('lookup_text')
            if lookup_table is True or lookup_text is not None:

                if lookup_table is True:
                    try:
                        v = int(v)
                        lookup_value = self.lookup_table.get(v)
                    except ValueError:
                        lookup_value = None
                else:
                    try:
                        v = int(lookup_text)
                        lookup_value = self.lookup_table_text.get(v)
                    except ValueError:
                        lookup_value = None

                if lookup_value:
                    v = lookup_value.get(
                        LANGUAGE_MAPPING[self.language], v)

            if return_list is True:
                return v
            else:
                return str(v)

        values = []

        for mapping in mappings:

            sub_mappings = mapping.get('mapping')
            if sub_mappings:
                sub_value = self.collect_mapping(
                    sub_mappings,
                    separator=mapping.get('composite', {}).get('separator'),
                    value_mapping_list=mapping.get(
                        'value_mapping_list', value_mapping_list),
                    return_list=return_list,
                    value_prefix=mapping.get('value_prefix', ''),
                    value_suffix=mapping.get('value_suffix', ''),
                    table_data=table_data,
                    no_duplicates=no_duplicates)
                if sub_value:

                    if mapping.get('conditions'):
                        if self.check_conditions(
                                mapping.get('conditions'),
                                mapping.get('condition_message'),
                                mapping.get('condition_message_opposite'),
                                mapping.get('conditions_join')) is False:
                            continue

                    if return_list is True:
                        values.extend(sub_value)
                    else:
                        values.append(sub_value)
                continue

            wocat_table = mapping.get('wocat_table')
            wocat_column = mapping.get('wocat_column')

            if return_row_values is True:
                # If the entire row values are to be returned, query only the
                # table data and return it as such (as dict).
                wocat_data = self.get_wocat_table_data(wocat_table)
                if wocat_data:
                    values.extend(wocat_data)
                continue

            if table_data is None:
                wocat_attribute = self.get_wocat_attribute_data(
                    table_name=wocat_table, attribute_name=wocat_column)
            else:
                table_attribute = table_data.get(wocat_column)
                if not table_attribute:
                    continue
                wocat_attribute = [table_attribute]

            if not wocat_attribute:
                continue

            if mapping.get('conditions'):
                if self.check_conditions(
                        mapping.get('conditions'),
                        mapping.get('condition_message'),
                        mapping.get('condition_message_opposite'),
                        mapping.get('conditions_join')) is False:
                    continue

            if mapping.get('index_filter'):
                index_filter = mapping.get('index_filter')
                if not isinstance(index_filter, list) or len(index_filter) != 1:
                    raise Exception(
                        'Index filter must be a list of exactly 1 item!')

                wocat_attribute = self.apply_index_filter(
                    values=wocat_attribute,
                    index_filter=index_filter[0])

            if mapping.get('mapping_message'):
                self.add_mapping_message(mapping.get('mapping_message'))

            for value in wocat_attribute:
                values.append(do_value_mapping(value))

        if no_duplicates is True:
            values = list(set(values))

        if return_list is True:
            return values

        if separator is None:
            separator = TEXT_VALUES_MERGE_CHAR

        values = separator.join(values)

        if values:
            return '{}{}{}'.format(value_prefix, values, value_suffix)

    def question_mapping(
            self, qcat_question_keyword, question_properties, table_data=None):
        """
        Do the mapping of a single or multiple WOCAT questions into a single
        QCAT question.

        Args:
            qcat_question_keyword: string.
            question_properties: dict.
            table_data: dict. An optional dictionary of WOCAT table data to be
                passed to the function collecting the mapping data.

        Returns:
            dict.
        """
        q_type = question_properties.get('type')
        if q_type is None:
            raise Exception('No type specified for question {}'.format(
                qcat_question_keyword))

        if q_type == 'constant':
            value = question_properties.get('value')
            return {
                qcat_question_keyword: value
            }

        mappings = question_properties.get('mapping')
        if mappings is None:
            raise Exception('No mapping specified for question {}'.format(
                qcat_question_keyword))

        if question_properties.get('conditions'):
            if self.check_conditions(
                    question_properties.get('conditions'),
                    question_properties.get('condition_message'),
                    question_properties.get('condition_message_opposite'),
                    question_properties.get('conditions_join')) is False:
                return {}

        no_duplicates = True if q_type in ['dropdown'] else False

        value = self.collect_mapping(
            mappings,
            separator=question_properties.get('composite', {}).get('separator'),
            value_mapping_list=question_properties.get('value_mapping_list'),
            value_prefix=question_properties.get('value_prefix', ''),
            value_suffix=question_properties.get('value_suffix', ''),
            no_duplicates=no_duplicates, table_data=table_data)

        if q_type == 'string':
            # For string values, also collect translations.

            values = []
            if value:
                values.append((self.language, value))

            # Collect translations
            for translated_import_object in self.translations:

                translated_value = translated_import_object.collect_mapping(
                    mappings,
                    separator=question_properties.get(
                        'composite', {}).get('separator'),
                    value_mapping_list=question_properties.get(
                        'value_mapping_list'),
                    value_prefix=question_properties.get('value_prefix', ''),
                    value_suffix=question_properties.get('value_suffix', ''),
                    table_data=table_data)

                if translated_value:
                    values.append(
                        (translated_import_object.language, translated_value))

            if not values:
                return {}

            ret_dict = {}
            for language, v in values:
                ret_dict[language] = v
            return {
                qcat_question_keyword: ret_dict
            }

        if not value:
            return {}

        if q_type == 'dropdown':
            try:
                value = int(value)
            except ValueError:
                pass
            return {
                qcat_question_keyword: value
            }

        elif q_type == 'date':
            try:
                value = datetime.strptime(
                    value, WOCAT_DATE_FORMAT).strftime(
                    QCAT_DATE_FORMAT)
            except ValueError:
                return {}

            return {
                qcat_question_keyword: value
            }

        elif q_type == 'file':
            value = self.handle_file(value)

            if not value:
                return {}

            return {
                qcat_question_keyword: value
            }

        else:
            raise NotImplementedError('Type {} is not valid'.format(q_type))

    def question_mapping_geom_point(
            self, qcat_question_keyword, question_properties):
        """
        Do the mapping of WOCAT questions into a geometry point GEOJSON question
        for QCAT.

        Args:
            qcat_question_keyword: string.
            question_properties: dict.

        Returns:
            dict.
        """
        mappings = question_properties.get('mapping')
        if mappings is None:
            raise Exception('No mapping specified for question {}'.format(
                qcat_question_keyword))

        values = self.collect_mapping(mappings, return_list=True)

        parsed_values = []
        for v in values:
            try:
                v = float(v)
            except ValueError:
                # Special cases

                int_values = [int(s) for s in re.findall(r'\b\d+\b', v)]
                if len(int_values) == 4:
                    # 38°35'52.48"N
                    v = int_values[0] + int_values[1] / 60 + \
                        (int_values[2] + int_values[3] / 100) / 3600
                elif len(int_values) == 3:
                    # 46 16 33
                    v = int_values[0] + int_values[1] / 60 + \
                        int_values[2] / 3600
                # Special cases for BHU001
                elif v == "N26 55.488'":
                    v = 26.9248
                elif v == "E089 20.439'":
                    v = 89.34065
                else:
                    self.output(
                        'Invalid coordinates ({}) of object {}'.format(
                            v, self.identifier),
                        v=1, l='error')
                    continue

            parsed_values.append(v)

        for v in parsed_values:
            # Basic coordinates test.
            if not -180 <= float(v) <= 180:
                self.add_error(
                    'mapping',
                    'Coordinates of object {} are not valid: {}'.format(
                        self, values))
                return None

        if len(parsed_values) == 2:
            geojson = {
                'type': 'FeatureCollection',
                'features': [
                    {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [parsed_values[1], parsed_values[0]]
                        },
                        'properties': None
                    }
                ]
            }
            return {
                qcat_question_keyword: json.dumps(geojson)
            }

        return {}

    def question_mapping_checkbox(
            self, qcat_question_keyword, question_properties):
        """
        Do the mapping of WOCAT questions into a checkbox question for QCAT.

        Args:
            qcat_question_keyword: string.
            question_properties: dict.

        Returns:
            dict.
        """
        mappings = question_properties.get('mapping')
        if mappings is None:
            raise Exception('No mapping specified for question {}'.format(
                qcat_question_keyword))

        values = self.collect_mapping(
            mappings,
            value_mapping_list=question_properties.get('value_mapping_list'),
            return_list=True)

        # Remove duplicates
        values = list(set(values))

        # Composite mapping options
        composite_mapping_option = question_properties.get(
            'composite', {}).get('mapping')

        if composite_mapping_option == 'exclusive':
            # Exclusive mapping means values which are not mapped will be
            # ignored.
            values = [v for v in values if v in question_properties.get(
                'value_mapping_list', {}).values()]

        if values:
            return {
                qcat_question_keyword: values
            }

    def row_mapping(self, qg_properties):
        """
        Collect and map WOCAT data by row.

        Args:
            qg_properties: dict.

        Returns:
            list.
        """

        """
        Transform the mapping so it is grouped by table and then by columns.
        {
            'questions': {
                'question_1': {
                    'mappings': [
                        {
                            'wocat_table': 'table_1',
                            'wocat_column': 'column_1',
                        }
                    ]
                }
            }
        }

        {
            'table_1': [
                {
                    'wocat_table': 'table_1',
                    'wocat_column': 'column_1',
                    'question': '',
                    'type': '',
                }
            ]
        }
        """
        mapping_order = None
        if qg_properties.get('mapping_order_column'):
            mapping_order = self.collect_mapping(
                [qg_properties.get('mapping_order_column')])
        mappings_by_table = OrderedDict()
        for q_name, q_properties in qg_properties.get('questions', {}).items():
            mappings = q_properties.get('mapping', [])

            # Order the mapping if necessary
            if mapping_order:
                mappings_ordered = []
                for order_entry in list(mapping_order):
                    ordered_entry = next((item for item in mappings if item.get(
                        'order_value') == order_entry), None)
                    if ordered_entry:
                        mappings_ordered.append(ordered_entry)
                if len(mappings_ordered) != len(mappings):
                    raise Exception(
                        'Something went wrong with the ordered mapping.')
                mappings = mappings_ordered

            for mapping in mappings:
                table_name = mapping.get('wocat_table')
                if table_name not in mappings_by_table:
                    mappings_by_table[table_name] = []
                mapping.update({
                    'question': q_name,
                    'type': q_properties.get('type'),
                })
                if mapping not in mappings_by_table[table_name]:
                    mappings_by_table[table_name].append(mapping)

        values = []
        for table_name, table_mappings in mappings_by_table.items():

            # Collect the rows for each table.
            fake_mappings = [{'wocat_table': table_name}]
            row_values = self.collect_mapping(
                fake_mappings, return_list=True, return_row_values=True)

            # Sort the values if necessary.
            sort_function = qg_properties.get('sort_function')
            if sort_function:
                row_values = sorted(
                    row_values, key=lambda k: eval(sort_function))

            # Get translations if available. Sort these values as well.
            translated_row_values = {}
            for translation_object in self.translations:
                translated_row = translation_object.collect_mapping(
                    fake_mappings, return_list=True, return_row_values=True)

                sort_function = qg_properties.get('sort_function')
                if sort_function:
                    translated_row = sorted(
                        translated_row, key=lambda k: eval(sort_function))

                translated_row_values[
                    translation_object.language] = translated_row

            for i, row_value in enumerate(row_values):
                # Put together the values of each row.

                value_entry = {}
                value_mapping_entries = {}
                for table_mapping in table_mappings:
                    column_name = table_mapping.get('wocat_column')
                    value_mapping = table_mapping.get('value_mapping')
                    question_name = table_mapping.get('question')
                    question_type = table_mapping.get('type')

                    if value_mapping is not None:
                        row_value.update({'value_mapping': value_mapping})
                        column_name = 'value_mapping'
                        value_mapping_entries[question_name] = value_mapping

                    if not column_name:
                        continue

                    single_value = row_value.get(column_name)
                    if not single_value:
                        continue

                    if question_type == 'string':
                        # For strings, also add the translations.
                        text_value = {self.language: single_value}

                        for lang, lang_data in translated_row_values.items():

                            if len(lang_data) != len(row_values):
                                self.add_mapping_message(
                                    'Number of translations for {} in language '
                                    '"{}" do not match the number of original '
                                    'entries.'.format(
                                        table_name,
                                        lang))

                            try:
                                translated_row = lang_data[i]
                            except IndexError:
                                continue

                            if len(translated_row) != len(row_value):
                                self.add_mapping_message(
                                    'Number of translations for {} in language '
                                    '"{}" do not match the number of original '
                                    'entries.'.format(
                                        table_name,
                                        lang))

                            translated_value = translated_row.get(column_name)
                            if translated_value is None:
                                continue

                            text_value[lang] = translated_value

                        single_value = text_value

                    value_entry[question_name] = single_value

                # If there are only the mapping entries in the value dict, skip
                # it.
                if value_entry == value_mapping_entries:
                    continue

                if qg_properties.get('unique', False) is True and value_entry in values:
                    continue

                if value_entry:
                    values.append(value_entry)

        return values

    def questiongroup_mapping(
            self, qcat_questiongroup_keyword, questiongroup_properties):
        """
        Map an entire Questiongroup of QCAT. Map each question and add the
        mapped data to the data json (data_json).

        Args:
            qcat_questiongroup_keyword: string.
            questiongroup_properties: dict.

        Returns:
            -
        """
        def single_questiongroup_mapping(
                qcat_qg_keyword, qg_properties, table_data=None):
            qg_data = {}
            for q_name, q_properties in qg_properties.get(
                    'questions', {}).items():

                if q_properties.get('conditions'):
                    if self.check_conditions(
                            q_properties.get('conditions'),
                            q_properties.get('condition_message'),
                            q_properties.get('condition_message_opposite'),
                            q_properties.get('conditions_join')) is False:
                        continue

                composite_type = q_properties.get('composite', {}).get('type')
                if composite_type is None or composite_type == 'merge':
                    q_data = self.question_mapping(
                        q_name, q_properties, table_data=table_data)

                elif composite_type == 'geom_point':
                    q_data = self.question_mapping_geom_point(
                        q_name, q_properties)

                elif composite_type == 'checkbox':
                    q_data = self.question_mapping_checkbox(
                        q_name, q_properties)

                else:
                    raise NotImplementedError()

                if q_data:
                    qg_data.update(q_data)

            existing_qg_data = self.data_json.get(qcat_qg_keyword, [])
            if qg_data:
                existing_qg_data.append(qg_data)
            if existing_qg_data:
                self.data_json[qcat_qg_keyword] = existing_qg_data

        qg_conditions = questiongroup_properties.get('conditions')
        if qg_conditions:
            if not self.check_conditions(
                    qg_conditions,
                    questiongroup_properties.get('condition_message'),
                    questiongroup_properties.get('condition_message_opposite'),
                    questiongroup_properties.get('conditions_join')):
                return

        if questiongroup_properties.get('repeating', False) is True:

            wocat_table = questiongroup_properties.get('wocat_table')
            if not wocat_table:
                raise Exception(
                    'Repeating questiongroups need to define a "wocat_table" '
                    'for the entire questiongroup.')

            wocat_table_data = self.get_wocat_table_data(wocat_table)
            if wocat_table_data is None:
                return

            if questiongroup_properties.get('sort_function'):
                wocat_table_data = sorted(wocat_table_data, key=lambda k: eval(
                    questiongroup_properties.get('sort_function')))

            for data in wocat_table_data:
                single_questiongroup_mapping(
                    qcat_questiongroup_keyword, questiongroup_properties,
                    table_data=data)

        elif questiongroup_properties.get('repeating_rows', False) is True:
            qg_data = self.row_mapping(questiongroup_properties)

            existing_qg_data = self.data_json.get(
                qcat_questiongroup_keyword, [])
            if qg_data:
                existing_qg_data.extend(qg_data)

            if existing_qg_data:
                self.data_json[qcat_questiongroup_keyword] = existing_qg_data

        elif questiongroup_properties.get('split_questions', False) is True:

            # Add special merging options
            for question_keyword, question_properties in questiongroup_properties.get(
                    'questions', {}).items():
                composite_options = question_properties.get('composite', {})
                composite_options.update({
                    'type': 'merge',
                    'separator': 'QUESTIONSEPARATOR'
                })
                question_properties['composite'] = composite_options
            single_questiongroup_mapping(
                qcat_questiongroup_keyword, questiongroup_properties)

            # Separate the data again
            questiongroup_data_list = self.data_json.get(
                qcat_questiongroup_keyword, [])

            grouped_questions = {}
            max_length = 0
            for questiongroup_data in questiongroup_data_list:
                for question_keyword, question_data in questiongroup_data.items():
                    grouped_questions[question_keyword] = {}
                    for lang, data in question_data.items():
                        data_split = data.split('QUESTIONSEPARATOR')
                        max_length = max(len(data_split), max_length)
                        grouped_questions[question_keyword][lang] = data_split

            new_data_list = []
            for i in range(max_length):
                new_data = {}
                for question_keyword, langs in grouped_questions.items():
                    new_data[question_keyword] = {}
                    for lang, data in langs.items():
                        try:
                            new_data[question_keyword][lang] = data[i]
                        except IndexError:
                            pass
                new_data_list.append(new_data)

            if new_data_list:
                self.data_json[qcat_questiongroup_keyword] = new_data_list

        else:
            single_questiongroup_mapping(
                qcat_questiongroup_keyword, questiongroup_properties)


class WOCATImport(Logger):

    import_objects_filter = []
    configuration_code = ''
    schema = ''
    lookup_table_name = ''
    lookup_table_name_text = ''
    file_info_table = ''
    image_url = ''
    questionnaire_identifier = ''
    questionnaire_code = ''
    questionnaire_owner = ''
    tables = []
    mapping = {}

    def __init__(self, command_options):
        self.command_options = command_options
        self.connection = psycopg2.connect(settings.WOCAT_IMPORT_DATABASE_URL)
        self.query_limit = 'NULL'

        # A collection of all objects to be imported.
        self.import_objects = []

        self.configuration = get_configuration(
            configuration_code=self.configuration_code)

    def collect_import_objects(self):
        """
        Collect all the objects to be imported. Query all WOCAT objects and
        collect all WOCAT data (wocat_data).

        Returns:

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

        self.output('Fetching data from WOCAT database.', v=1)

        # Try to query the lookup table and collect its values.
        try:
            lookup_query = """
                SELECT *
                FROM {schema}.{table_name};
            """.format(schema=self.schema, table_name=self.lookup_table_name)
            lookup_table = {}
            for row in etl.dicts(etl.fromdb(self.connection, lookup_query)):
                lookup_table[row.get('id')] = row
        except AttributeError:
            lookup_table = {}

        # Try to query the TEXT lookup table and collect its values.
        try:
            lookup_query_text = """
                SELECT *
                FROM {schema}.{table_name};
            """.format(schema=self.schema,
                       table_name=self.lookup_table_name_text)
            lookup_table_text = {}
            for row in etl.dicts(
                    etl.fromdb(self.connection, lookup_query_text)):
                lookup_table_text[row.get('id')] = row
        except AttributeError:
            lookup_table_text = {}

        # Try to query file infos
        try:
            lookup_query_files = """
                SELECT *
                FROM {schema}.{table_name};
            """.format(schema=self.schema,
                       table_name=self.file_info_table)
            file_infos = {}
            for row in etl.dicts(
                    etl.fromdb(self.connection, lookup_query_files)):
                file_infos[row.get('blob_id')] = row
        except AttributeError:
            file_infos = {}

        # Determine all tables which need to be queried.
        all_tables = self.tables
        for qg_properties in self.mapping.values():
            questions = qg_properties.get('questions', {})
            for q_properties in questions.values():
                all_tables.extend(get_tables(q_properties.get('mapping', [])))

        # Remove duplicates
        all_tables = list(set(all_tables))

        # Query each table and collect the values.
        for table_name in all_tables:
            query = """
                SELECT {tables}
                FROM {schema}.{table_name}
                LIMIT {limit};
            """.format(
                tables='*', schema=self.schema, table_name=table_name,
                limit=self.query_limit
            )

            queried_table = etl.fromdb(self.connection, query)
            for row in etl.dicts(queried_table):
                identifier = row.get(self.questionnaire_identifier)

                import_object = self.get_import_object(identifier)

                if import_object is None:
                    import_object = ImportObject(
                        identifier, self.command_options, lookup_table,
                        lookup_table_text, file_infos, self.image_url)

                    import_object.add_custom_mapping_messages(
                        self.custom_mapping_messages)

                    self.import_objects.append(import_object)

                # If the code is available in the current table data, set it.
                code = row.get(self.questionnaire_code)
                if code:
                    import_object.set_code(code)

                questionnaire_owner = row.get(self.questionnaire_owner)
                if questionnaire_owner:
                    import_object.set_owner(questionnaire_owner)

                # If the creation date is available in the current table data,
                # set it.
                created = row.get('insert_date')
                if created:
                    import_object.created = timezone.make_aware(
                        created, timezone.get_current_timezone())

                import_object.add_wocat_data(table_name, row)

        self.output('{} objects found.'.format(
            len(self.import_objects)), v=1)

    def filter_import_objects(self):
        """
        Filter the import objects based on status and custom filters.

        Returns:
            -
        """
        # Status filter: qt.qt_quality_review.quality_review = 372 | 373
        # 372: Complete
        # 373: Incomplete
        # status_objects = []
        # for import_object in self.import_objects:
        #     not_review_content = import_object.get_wocat_attribute_data(
        #         table_name='qt_quality_review',
        #         attribute_name='not_review_content')
        #     if 372 in not_review_content or 373 in not_review_content:
        #         status_objects.append(import_object)
        # self.import_objects = status_objects

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

    def check_translations(self):
        """
        Check if an import object has translations, determine the original and
        link its translations. Keep only originals in import_objects.

        Returns:
            -
        """
        processed_codes = []
        original_import_objects = []

        for import_object in self.import_objects:

            code = import_object.code

            # Process each code only once
            if code in processed_codes:
                continue
            processed_codes.append(code)

            same_code_objects = [
                io for io in self.import_objects if io.code == code]

            if len(same_code_objects) == 1:
                # Only one translation available -> it is already the original
                original_import_objects.append(import_object)
                continue

            same_code_objects_sorted = sorted(
                same_code_objects, key=lambda el: el.created)

            original = same_code_objects_sorted[0]
            translations = same_code_objects_sorted[1:]

            for translation in translations:
                original.translations.append(translation)

            original_import_objects.append(original)

        self.import_objects = original_import_objects

        self.output('{} objects remained after merging translations.'.format(
            len(self.import_objects)), v=1)

    def get_import_object(self, identifier):
        """
        Access a single import object by its identifier.

        Args:
            identifier:

        Returns:
            ImportObject.
        """
        return next((item for item in self.import_objects if
                     item.identifier == identifier), None)

    def do_mapping(self):
        """
        Do the mapping of each ImportObject.

        Returns:
            -
        """
        self.output('Starting mapping of data ...', v=1)
        for import_object in self.import_objects:
            for qg_name, qg_properties in self.mapping.items():
                import_object.questiongroup_mapping(qg_name, qg_properties)

    def print_errors(self):
        """
        Print all errors of each ImportObject encountered.

        Returns:
            -
        """
        error_objects_count = 0
        error_count = 0
        for import_object in self.import_objects:
            if import_object.has_errors():
                import_object.print_errors()
                error_objects_count += 1
                error_count += import_object.get_error_count()
        if error_objects_count > 0:
            self.output('{} errors found in {} objects. Not importing.'.format(
                error_count, error_objects_count), l='error')

    def print_error_list(self):
        """
        Print a list of all ImportObjects which contain errors.

        Returns:
            -
        """
        self.output('Error list:')
        for import_object in self.import_objects:
            if import_object.has_errors():
                print(import_object)

    def save_objects(self):
        """
        Handle the actual insert of the ImportObjects. Only insert if there are
        no errors.

        Returns:
            -
        """
        has_errors = False

        # Check the objects first.
        self.output('Checking data ...', v=1)
        for import_object in self.import_objects:
            import_object.check(self.configuration)
            self.output('\nData JSON of {} | {}'.format(
                import_object.identifier, import_object.code), v=3)
            self.output(import_object.data_json, v=3, pretty=True)
            has_errors |= import_object.has_errors()

        if has_errors:
            self.output('Errors listed below.', l='error')
            self.print_errors()
            if self.command_options.get('error-list'):
                self.print_error_list()
            return

        else:
            self.output('No errors encountered.', v=1)

        mapping_messages_count = 0
        for import_object in self.import_objects:
            if import_object.mapping_messages:
                mapping_messages_count += 1
                self.output('\nMapping messages for {}:\n{}'.format(
                    import_object, '\n'.join(import_object.get_mapping_messages())), v=3)
        self.output('{} objects with mapping messages.'.format(mapping_messages_count), v=2)

        dry_run = self.command_options['dry-run']
        if not dry_run:

            # Deactivate signal which creates notifications
            signals.create_questionnaire.disconnect(create_questionnaire)

            inserted = []
            self.output('Starting insert of objects ...', v=1)
            for import_object in self.import_objects:
                inserted_object = import_object.save(self.configuration)
                import_object.questionnaire_object = inserted_object
                inserted.append(inserted_object)

            # Reactivate notification signal
            signals.create_questionnaire.connect(create_questionnaire)

            self.output('{} objects inserted.'.format(len(inserted)), v=0, l='success')
        else:
            self.output(
                'Dry-run mode is on, not importing anything.', v=0, l='warning')

        write_mapping_messages = self.command_options['mapping-messages']
        if write_mapping_messages:
            self.write_mapping_messages()

    def write_mapping_messages(self):

        file = open(MAPPING_MESSAGES_FILENAME, 'w')
        configuration = get_configuration('technologies')

        print('Mapping messages of WOCAT import on {}\n\n'.format(
            datetime.now()), file=file)

        for import_object in self.import_objects:

            print('WOCAT Code: {}'.format(import_object.code), file=file)
            print('WOCAT ID: {}'.format(import_object.identifier), file=file)
            qcat_code = '-'
            qcat_url = ''
            questionnaire_name = ''
            translations = []
            if import_object.questionnaire_object is not None:
                questionnaire_object = import_object.questionnaire_object
                qcat_code = questionnaire_object.code
                translations = questionnaire_object.translations
                activate(questionnaire_object.original_locale)
                qcat_url = reverse(
                    'technologies:questionnaire_details', args=[qcat_code])
                name_dict = configuration.get_questionnaire_name(
                    questionnaire_object.data)
                questionnaire_name = name_dict.get(
                    questionnaire_object.original_locale, 'Unknown Name')

            print('QCAT Code: {}'.format(qcat_code), file=file)
            print('URL: https://qcat.wocat.net{}'.format(qcat_url), file=file)
            print('Name: {}'.format(questionnaire_name), file=file)
            if translations:
                print(
                    'Original language: {} | Translations: {}'.format(
                        translations[:1][0], ', '.join(translations[1:] or '-')),
                    file=file)
            print('Mapping messages:\n{}'.format('\n'.join(
                import_object.get_mapping_messages())), file=file)

            print('\n', file=file)

        self.output('Wrote mapping messages to file {}.'.format(
            MAPPING_MESSAGES_FILENAME), v=1)


class QTImport(WOCATImport):
    """
    Contains all the specifications for the import of the WOCAT QT data.
    """

    schema = 'qt'

    # Tables of the mapping are collected automatically.
    tables = [
        'qt_questionnaire_info',
        'qt_quality_review',
        'qt_1'
    ]
    lookup_table_name = 'qt_lk_general'
    lookup_table_name_text = 'qt_lk_text'
    """
    SELECT * FROM qt.qt_lk_text WHERE english LIKE '%FOO%';
    """
    file_info_table = 'qt_blob_info'
    image_url = 'https://qt.wocat.net/thumbnail.php?blob_id={}'

    questionnaire_identifier = 'qt_id'
    questionnaire_code = 'technology_code'
    configuration_code = 'technologies'
    questionnaire_owner = 'owner_id'

    mapping = qt_mapping
    custom_mapping_messages = custom_mapping_messages

    # Optionally specify a list of IDs (qt_id) to filter the QT Questionnaires.
    import_objects_filter = []

    def __init__(self, command_options):
        super().__init__(command_options)
        self.output("\n-- WOCAT QT.\n", v=1)
