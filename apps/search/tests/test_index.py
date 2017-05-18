import uuid
import logging

from django.conf import settings
from django.test.utils import override_settings
from elasticsearch import TransportError
from unittest.mock import patch, Mock

from configuration.cache import get_configuration
from configuration.configuration import QuestionnaireConfiguration
from qcat.tests import TestCase
from questionnaire.models import Questionnaire
from questionnaire.serializers import QuestionnaireSerializer
from questionnaire.tests.test_models import get_valid_questionnaire
from search.index import (
    create_or_update_index,
    delete_all_indices,
    delete_questionnaires_from_es,
    delete_single_index,
    get_current_and_next_index,
    get_elasticsearch,
    get_mappings,
    put_questionnaire_data,
)
from ..search import simple_search

# Prevent logging of Elasticsearch queries
logging.disable(logging.CRITICAL)


es = get_elasticsearch()
TEST_INDEX_PREFIX = 'qcat_test_prefix_'
TEST_ALIAS = uuid.uuid4()
TEST_ALIAS_PREFIXED = '{}{}'.format(TEST_INDEX_PREFIX, TEST_ALIAS)
TEST_INDEX = '{}_1'.format(TEST_ALIAS_PREFIXED)


def create_temp_indices(indices):
    """
    For each index, create the index and update it with the
    questionnaires of the corresponding configuration as found in the
    database.

    Make sure to override the settings and use a custom prefix for the
    indices.
    """
    for index in indices:
        configuration = QuestionnaireConfiguration(index)
        mappings = get_mappings(configuration)
        create_or_update_index(index, mappings)
        put_questionnaire_data(
            index, Questionnaire.objects.filter(
                configurations__code=index).filter(status=4))


class GetMappingsTest(TestCase):
    def test_calls_get_questiongroups(self):
        mock_Conf = Mock()
        mock_Conf.get_questiongroups.return_value = []
        get_mappings(mock_Conf)
        mock_Conf.get_questiongroups.assert_called_once_with()

    def test_returns_dictionary(self):
        mock_Conf = Mock()
        mock_Conf.get_questiongroups.return_value = []
        mappings = get_mappings(mock_Conf)
        self.assertIsInstance(mappings, dict)
        self.assertIn('questionnaire', mappings)
        self.assertIn('properties', mappings['questionnaire'])
        self.assertIn('data', mappings['questionnaire']['properties'])

    def test_adds_each_questiongroup(self):
        mock_Conf = Mock()
        mock_qg_1 = Mock()
        mock_qg_1.questions = []
        mock_qg_1.keyword = 'foo'
        mock_qg_2 = Mock()
        mock_qg_2.questions = []
        mock_qg_2.keyword = 'bar'
        mock_Conf.get_questiongroups.return_value = [mock_qg_1, mock_qg_2]
        mappings = get_mappings(mock_Conf)
        qgs = mappings.get('questionnaire', {}).get('properties', {}).get(
            'data', {}).get('properties')
        self.assertEqual(len(qgs), 2+len(settings.QUESTIONNAIRE_GLOBAL_QUESTIONGROUPS))
        for qg_name in ['foo', 'bar']:
            qg = qgs.get(qg_name)
            self.assertEqual(qg.get('type'), 'nested')
            self.assertEqual(qg.get('properties'), {})

    @override_settings(ES_ANALYZERS=(('en', 'english'), ('es', 'spanish')))
    def test_adds_analyzer_for_strings(self):
        mock_Conf = Mock()
        mock_q_1 = Mock()
        mock_q_1.keyword = 'a'
        mock_q_1.field_type = 'char'
        mock_q_2 = Mock()
        mock_q_2.keyword = 'b'
        mock_q_2.field_type = 'char'
        mock_qg_1 = Mock()
        mock_qg_1.questions = [mock_q_1, mock_q_2]
        mock_qg_1.keyword = 'foo'
        mock_Conf.get_questiongroups.return_value = [mock_qg_1]
        mappings = get_mappings(mock_Conf)
        qgs = mappings.get('questionnaire', {}).get('properties', {}).get(
            'data', {}).get('properties')
        self.assertEqual(len(qgs), 1+len(settings.QUESTIONNAIRE_GLOBAL_QUESTIONGROUPS))
        qs = qgs.get('foo', {}).get('properties', {})
        for q_name in ['a', 'b']:
            q = qs.get(q_name)
            self.assertEqual(
                q.get('properties').get('es'),
                {'analyzer': 'spanish', 'type': 'string'})
            self.assertEqual(
                q.get('properties').get('en'),
                {'analyzer': 'english', 'type': 'string'})

    def test_adds_basic_mappings(self):
        mock_Conf = Mock()
        mock_Conf.get_questiongroups.return_value = []
        mappings = get_mappings(mock_Conf)
        q_props = mappings.get('questionnaire').get('properties')
        self.assertEqual(len(q_props), 11)
        default_props = {}
        for global_questiongroup in settings.QUESTIONNAIRE_GLOBAL_QUESTIONGROUPS:
            default_props[global_questiongroup] = {'properties': {}, 'type': 'nested'}
        self.assertEqual(q_props['data'], {'properties': default_props})
        self.assertEqual(q_props['created'], {'type': 'date'})
        self.assertEqual(q_props['updated'], {'type': 'date'})
        self.assertEqual(q_props['translations'], {'type': 'string'})
        self.assertEqual(q_props['configurations'], {'type': 'string'})
        self.assertEqual(q_props['code'], {'type': 'string'})
        self.assertIn('name', q_props)
        self.assertIn('links', q_props)
        self.assertEqual(
            q_props['compilers'],
            {'type': 'nested', 'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'}}})
        self.assertEqual(
            q_props['editors'],
            {'type': 'nested', 'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'}}})


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class CreateOrUpdateIndexTest(TestCase):

    fixtures = ['sample.json', 'sample_global_key_values.json']

    def setUp(self):
        """
        Create a new index with a random name for testing. Will be deleted
        after the tests ran.
        """
        try:
            es.indices.create(index=TEST_INDEX)
            es.indices.put_alias(index=TEST_INDEX, name=TEST_ALIAS_PREFIXED)
        except TransportError:
            raise Exception(
                'No connection to Elasticsearch possible. Make sure it is '
                'running and the configuration is correct.')
        self.default_body = {
            'settings': {'index': {'mapping': {
                'nested_fields': {'limit': 250}}}
            }, 'mappings': {}}

    def tearDown(self):
        """
        Delete the index used for testing.

        Use the following to delete all test indices::
            curl -XDELETE '[ES_HOST]:[ES_PORT]/[TEST_INDEX_PREFIX]*'

        Example::
            curl -XDELETE 'http://localhost:9200/qcat_test_prefix_*'
        """
        try:
            es.indices.delete(index='{}*'.format(TEST_INDEX_PREFIX))
        except TransportError:
            raise Exception(
                'Index of Elasticsearch could not be deleted, manual cleanup '
                'necessary.')

    @patch('search.index.get_alias')
    def test_calls_get_alias(self, mock_get_alias):
        mock_get_alias.return_value = 'foo'
        create_or_update_index('foo', {})
        mock_get_alias.assert_called_once_with(['foo'])

    @patch('search.index.es')
    def test_calls_indices_exists_alias(self, mock_es):
        create_or_update_index('foo', {})
        mock_es.indices.exists_alias.assert_called_once_with(
            name='{}foo'.format(TEST_INDEX_PREFIX))

    @patch('search.index.es')
    def test_calls_indices_create_if_no_alias(self, mock_es):
        mock_es.indices.exists_alias.return_value = False
        create_or_update_index('foo', {})
        mock_es.indices.create.assert_called_once_with(
            index='{}foo_1'.format(TEST_INDEX_PREFIX), body=self.default_body)

    @patch('search.index.es')
    def test_calls_indices_put_alias_if_no_alias(self, mock_es):
        mock_es.indices.exists_alias.return_value = False
        mock_es.indices.create.return_value = {'acknowledged': True}
        create_or_update_index('foo', {})
        mock_es.indices.put_alias.assert_called_once_with(
            index='{}foo_1'.format(TEST_INDEX_PREFIX),
            name='{}foo'.format(TEST_INDEX_PREFIX))

    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_get_current_index_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index):
        mock_es.indices.exists_alias.return_value = True
        mock_get_current_and_next_index.return_value = 'a', 'b'
        create_or_update_index('foo', {})
        mock_get_current_and_next_index.assert_called_once_with(
            '{}foo'.format(TEST_INDEX_PREFIX))

    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_create_index_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index):
        mock_es.indices.exists_alias.return_value = True
        mock_get_current_and_next_index.return_value = 'a', 'b'
        create_or_update_index('foo', {})
        mock_es.indices.create.assert_called_once_with(
            index='b', body=self.default_body)

    @patch('search.index.reindex')
    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_reindex_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index, mock_reindex):
        mock_es.indices.exists_alias.return_value = True
        mock_es.indices.create.return_value = {'acknowledged': True}
        mock_get_current_and_next_index.return_value = 'a', 'b'
        mock_reindex.return_value = 0, []
        create_or_update_index('foo', {})
        mock_reindex.assert_called_once_with(mock_es, 'a', 'b')

    @patch('search.index.reindex')
    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_refresh_indices_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index, mock_reindex):
        mock_es.indices.exists_alias.return_value = True
        mock_es.indices.create.return_value = {'acknowledged': True}
        mock_get_current_and_next_index.return_value = 'a', 'b'
        mock_reindex.return_value = 0, []
        create_or_update_index('foo', {})
        mock_es.indices.refresh.assert_called_once_with(index='b')

    @patch('search.index.reindex')
    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_put_alias_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index, mock_reindex):
        mock_es.indices.exists_alias.return_value = True
        mock_es.indices.create.return_value = {'acknowledged': True}
        mock_get_current_and_next_index.return_value = 'a', 'b'
        mock_reindex.return_value = 0, []
        create_or_update_index('foo', {})
        mock_es.indices.put_alias.assert_called_once_with(
            index='b', name='{}foo'.format(TEST_INDEX_PREFIX))

    @patch('search.index.reindex')
    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_delete_alias_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index, mock_reindex):
        mock_es.indices.exists_alias.return_value = True
        mock_es.indices.create.return_value = {'acknowledged': True}
        mock_get_current_and_next_index.return_value = 'a', 'b'
        mock_reindex.return_value = 0, []
        mock_es.indices.put_alias.return_value = {'acknowledged': True}
        create_or_update_index('foo', {})
        mock_es.indices.delete_alias.assert_called_once_with(
            index='a', name='{}foo'.format(TEST_INDEX_PREFIX))

    @patch('search.index.reindex')
    @patch('search.index.get_current_and_next_index')
    @patch('search.index.es')
    def test_calls_delete_if_alias_exists(
            self, mock_es, mock_get_current_and_next_index, mock_reindex):
        mock_es.indices.exists_alias.return_value = True
        mock_es.indices.create.return_value = {'acknowledged': True}
        mock_get_current_and_next_index.return_value = 'a', 'b'
        mock_reindex.return_value = 0, []
        mock_es.indices.put_alias.return_value = {'acknowledged': True}
        mock_es.indices.delete_alias.return_value = {'acknowledged': True}
        create_or_update_index('foo', {})
        mock_es.indices.delete.assert_called_once_with(index='a')

    def test_creates_new_index(self):
        alias = uuid.uuid4()
        alias_prefixed = '{}{}'.format(TEST_INDEX_PREFIX, alias)
        index = '{}{}_1'.format(TEST_INDEX_PREFIX, alias)
        self.assertFalse(es.indices.exists_alias(name=alias_prefixed))
        self.assertFalse(es.indices.exists(index=index))
        create_or_update_index(alias, {})
        self.assertTrue(es.indices.exists_alias(name=alias_prefixed))
        self.assertTrue(es.indices.exists(index=index))
        es.indices.delete(index=index)

    def test_updates_index(self):
        # An index and alias exists already
        self.assertTrue(es.indices.exists_alias(name=TEST_ALIAS_PREFIXED))
        current_index, next_index = get_current_and_next_index(
            TEST_ALIAS_PREFIXED)
        self.assertTrue(es.indices.exists(index=current_index))
        # The index is updated
        create_or_update_index(TEST_ALIAS, {})
        # There is still an alias
        self.assertTrue(es.indices.exists_alias(name=TEST_ALIAS_PREFIXED))
        # The old index does not exist anymore
        self.assertFalse(es.indices.exists(index=current_index))
        # A new index has been created
        self.assertTrue(
            es.indices.exists(index=next_index))

    def test_keeps_data(self):
        m = get_valid_questionnaire()
        put_questionnaire_data(TEST_ALIAS, [m])
        search = simple_search('bar', configuration_codes=[TEST_ALIAS])
        hits = search.get('hits', {}).get('hits', [])
        self.assertEqual(len(hits), 1)
        create_or_update_index(TEST_ALIAS, {})
        search = simple_search('bar', configuration_codes=[TEST_ALIAS])
        hits = search.get('hits', {}).get('hits', [])
        self.assertEqual(len(hits), 1)

    def test_returns_correct_values(self):
        success, logs, error_msg = create_or_update_index(TEST_ALIAS, {})
        self.assertIsInstance(success, bool)
        self.assertTrue(success)
        self.assertIsInstance(logs, list)
        self.assertEqual(len(logs), 7)
        self.assertEqual(error_msg, '')

    @patch('search.index.force_strings')
    def test_calls_force_string(self, mock_force_strings):
        m = get_valid_questionnaire()
        mock_force_strings.return_value = {}
        put_questionnaire_data(TEST_ALIAS, [m])
        mock_force_strings.assert_called_once_with({})


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class PutQuestionnaireDataTest(TestCase):

    fixtures = ['sample.json', 'sample_global_key_values.json']

    @patch('search.index.es')
    @patch('search.index.ConfigurationList')
    def test_creates_configuration_list(self, mock_ConfList, mock_es):
        put_questionnaire_data('foo', [])
        mock_ConfList.assert_called_once_with()

    @patch('search.index.es')
    @patch('search.index.get_alias')
    def test_calls_get_alias(self, mock_get_alias, mock_es):
        put_questionnaire_data('foo', [])
        mock_get_alias.assert_called_once_with(['foo'])

    @patch('search.index.es')
    @patch('search.index.bulk')
    def test_calls_bulk(self, mock_bulk, mock_es):
        mock_bulk.return_value = 0, []
        questionnaire = get_valid_questionnaire()
        put_questionnaire_data('foo', [questionnaire])
        source = dict(QuestionnaireSerializer(
            questionnaire,
            config=get_configuration('foo')
        ).data)
        data = [{
            '_index': '{}foo'.format(TEST_INDEX_PREFIX),
            '_type': 'questionnaire',
            '_id': questionnaire.id,
            '_source': source
        }]
        mock_bulk.assert_called_once_with(mock_es, data)

    @patch('search.index.es')
    def test_calls_indices_refresh(self, mock_es):
        put_questionnaire_data('foo', [])
        mock_es.indices.refresh.assert_called_once_with(
            index='{}foo'.format(TEST_INDEX_PREFIX))

    @patch('search.index.es')
    @patch('search.index.bulk')
    def test_returns_values(self, mock_bulk, mock_es):
        mock_bulk.return_value = 'foo', 'bar'
        actions, errors = put_questionnaire_data('foo', [])
        self.assertEqual(actions, 'foo')
        self.assertEqual(errors, 'bar')


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class DeleteQuestionnairesFromEsTest(TestCase):
    def setUp(self):
        self.objects = [Mock()]

    @patch('search.index.es')
    def test_calls_indices_delete(self, mock_es):
        delete_questionnaires_from_es('sample', self.objects)
        mock_es.delete.assert_called_once_with(
            index='{}{}'.format(TEST_INDEX_PREFIX, 'sample'),
            doc_type='questionnaire', id=self.objects[0].id)

    def test_fails_silently_if_no_such_object(self):
        delete_questionnaires_from_es('sample', self.objects)


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class DeleteAllIndicesTest(TestCase):
    @patch('search.index.es')
    def test_calls_indices_delete(self, mock_es):
        delete_all_indices()
        mock_es.indices.delete.assert_called_once_with(index='{}*'.format(
            TEST_INDEX_PREFIX))

    @patch('search.index.es')
    def test_returns_false_if_no_success(self, mock_es):
        mock_es.indices.delete.return_value = {'acknowledged': False}
        success, error_msg = delete_all_indices()
        self.assertFalse(success)
        self.assertEqual(error_msg, 'Indices could not be deleted')

    @patch('search.index.es')
    def test_returns_true_if_no_success(self, mock_es):
        mock_es.indices.delete.return_value = {'acknowledged': True}
        success, error_msg = delete_all_indices()
        self.assertTrue(success)
        self.assertEqual(error_msg, '')


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class DeleteSingleIndexTest(TestCase):
    @patch('search.index.es')
    def test_calls_indices_delete(self, mock_es):
        delete_single_index('index')
        mock_es.indices.delete.assert_called_once_with(index='{}{}'.format(
            TEST_INDEX_PREFIX, 'index'), ignore=[404])

    @patch('search.index.es')
    def test_returns_false_if_no_success(self, mock_es):
        mock_es.indices.delete.return_value = {'acknowledged': False}
        success, error_msg = delete_single_index('index')
        self.assertFalse(success)
        self.assertEqual(error_msg, 'Index could not be deleted')

    @patch('search.index.es')
    def test_returns_true_if_no_success(self, mock_es):
        mock_es.indices.delete.return_value = {'acknowledged': True}
        success, error_msg = delete_single_index('index')
        self.assertTrue(success)
        self.assertEqual(error_msg, '')
