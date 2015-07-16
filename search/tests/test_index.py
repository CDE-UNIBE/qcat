# Prevent logging of Elasticsearch queries
import logging
logging.disable(logging.CRITICAL)

import uuid
from django.test.utils import override_settings
from elasticsearch import TransportError
from unittest.mock import patch, Mock

from configuration.configuration import QuestionnaireConfiguration
from qcat.tests import TestCase
from questionnaire.models import Questionnaire
from questionnaire.tests.test_models import get_valid_metadata
from search.index import (
    create_or_update_index,
    delete_all_indices,
    get_current_and_next_index,
    get_elasticsearch,
    get_mappings,
    put_questionnaire_data,
)
from search.search import (
    simple_search,
)


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
            index, Questionnaire.objects.filter(configurations__code=index))


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
        self.assertEqual(len(qgs), 2)
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
        self.assertEqual(len(qgs), 1)
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
        self.assertEqual(len(q_props), 8)
        self.assertEqual(q_props['data'], {'properties': {}})
        self.assertEqual(q_props['created'], {'type': 'date'})
        self.assertEqual(q_props['updated'], {'type': 'date'})
        self.assertEqual(q_props['translations'], {'type': 'string'})
        self.assertEqual(q_props['configurations'], {'type': 'string'})
        self.assertEqual(q_props['code'], {'type': 'string'})
        self.assertIn('name', q_props)
        self.assertEqual(
            q_props['authors'],
            {'type': 'nested', 'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'}}})


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class CreateOrUpdateIndexTest(TestCase):

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
            index='{}foo_1'.format(TEST_INDEX_PREFIX), body={'mappings': {}})

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
            index='b', body={'mappings': {}})

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
        m = Mock()
        m.configurations.all.return_value = []
        m.questionnairetranslation_set.all.return_value = []
        m.id = 1
        m.data = [{"foo": "bar"}]
        m.created = ''
        m.updated = ''
        m.code = ''
        m.members.filter.return_value = []
        m.get_metadata.return_value = {}
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


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class PutQuestionnaireDataTest(TestCase):

    @patch('search.index.es')
    @patch.object(QuestionnaireConfiguration, '__init__')
    def test_creates_questionnaire_configuration(
            self, mock_QuestionnaireConfiguration, mock_es):
        mock_QuestionnaireConfiguration.return_value = None
        put_questionnaire_data('foo', [])
        mock_QuestionnaireConfiguration.assert_called_once_with('foo')

    @patch('search.index.es')
    @patch('search.index.get_alias')
    def test_calls_get_alias(self, mock_get_alias, mock_es):
        put_questionnaire_data('foo', [])
        mock_get_alias.assert_called_once_with(['foo'])

    @patch('search.index.es')
    @patch('search.index.bulk')
    def test_calls_get_metadata(self, mock_bulk, mock_es):
        mock_bulk.return_value = 0, []
        m = Mock()
        m.configurations.all.return_value = []
        m.questionnairetranslation_set.all.return_value = []
        m.members.filter.return_value = []
        m.get_metadata.return_value = get_valid_metadata()
        put_questionnaire_data('foo', [m])
        m.get_metadata.assert_called_once_with()

    @patch('search.index.es')
    @patch('search.index.bulk')
    def test_calls_bulk(self, mock_bulk, mock_es):
        mock_bulk.return_value = 0, []
        m = Mock()
        m.configurations.all.return_value = []
        m.questionnairetranslation_set.all.return_value = []
        m.members.filter.return_value = []
        m.get_metadata.return_value = get_valid_metadata()
        put_questionnaire_data('foo', [m])
        data = [{
            '_index': '{}foo'.format(TEST_INDEX_PREFIX),
            '_type': 'questionnaire',
            '_id': m.id,
            '_source': {
                'data': m.data,
                'list_data': {},
                'created': 'created',
                'updated': 'updated',
                'code': 'code',
                'name': {'en': 'Unknown name'},
                'configurations': ['configuration'],
                'translations': ['en'],
                'authors': ['author'],
            }
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
