import logging
from unittest.mock import patch, MagicMock, sentinel

from django.conf import settings
from django.http import Http404
from django.test import RequestFactory
from django.test import override_settings
from rest_framework.test import force_authenticate, APIRequestFactory
from rest_framework.response import Response

from accounts.tests.test_models import create_new_user
from qcat.tests import TestCase
from questionnaire.models import Questionnaire
from questionnaire.serializers import QuestionnaireSerializer
from questionnaire.api.views import QuestionnaireListView, \
    QuestionnaireDetailView,  QuestionnaireAPIMixin, \
    ConfiguredQuestionnaireDetailView
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices


TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class QuestionnaireListViewTest(TestCase):
    fixtures = ['sample', 'sample_questionnaires']

    def setUp(self):
        delete_all_indices()
        create_temp_indices(['sample'])
        self.factory = RequestFactory()
        self.url = '/en/api/v1/questionnaires/sample_1/'
        self.request = self.factory.get(self.url)
        self.request.version = 'v1'
        self.view = self.setup_view(
            QuestionnaireListView(), self.request, identifier='sample_1'
        )

    def tearDown(self):
        delete_all_indices()

    @patch('questionnaire.api.views.advanced_search')
    def test_logs_call(self, mock_advanced_search):
        """
        Use the requestfactory from the rest-framework, as this handles the
        custom token authentication nicely.
        """
        user = create_new_user()
        request = APIRequestFactory().get(self.url)
        force_authenticate(request, user=user)
        with patch('api.models.RequestLog.save') as mock_save:
            QuestionnaireListView().dispatch(request)
            mock_save.assert_called_once_with()

    def test_api_detail_url(self):
        questionnaire = Questionnaire.objects.get(code='sample_1')
        serialized = QuestionnaireSerializer(questionnaire).data
        item = self.view.replace_keys(serialized)
        self.assertEqual(
            item.get('api_url'), '/en/api/v1/questionnaires/sample_1/'
        )

    def test_current_page(self):
        request = self.factory.get('{}?page=5'.format(self.url))
        request.version = 'v1'
        view = self.setup_view(self.view, request, identifier='sample_1')
        view.get_elasticsearch_items()
        self.assertEqual(view.current_page, 5)

    @patch('questionnaire.api.views.advanced_search')
    def test_access_elasticsearch(self, mock_advanced_search):
        mock_advanced_search.return_value = {}
        self.view.get(self.request)
        mock_advanced_search.assert_called_once_with(
            limit=settings.API_PAGE_SIZE,
            offset=0
        )

    @patch('questionnaire.api.views.advanced_search')
    def test_pagination(self, mock_advanced_search):
        mock_advanced_search.return_value = {}
        with patch('questionnaire.view_utils.ESPagination.__init__') as mock:
            mock.return_value = None
            self.view.get_es_paginated_results(0)
            mock.assert_called_once_with([], 0)

    @patch('questionnaire.api.views.QuestionnaireListView._get_paginate_link')
    def test_next_link(self, mock_get_paginate_link):
        view = self.setup_view(self.view, self.request, identifier='sample_1')
        view.current_page = 2
        view.get_next_link()
        mock_get_paginate_link.assert_called_with(3)

    @patch('questionnaire.api.views.QuestionnaireListView._get_paginate_link')
    def test_previous_links(self, mock_get_paginate_link):
        view = self.setup_view(self.view, self.request, identifier='sample_1')
        view.current_page = 2
        view.get_previous_link()
        mock_get_paginate_link.assert_called_with(1)

    @patch('questionnaire.api.views.advanced_search')
    def test_response_type(self, mock_advanced_search):
        mock_advanced_search.return_value = {}
        response = self.view.get(self.request)
        self.assertIsInstance(response, Response)

    @override_settings(QUESTIONNAIRE_API_CHANGE_KEYS={'foo': 'bar'})
    @patch('questionnaire.api.views.get_configuration')
    def test_replace_keys(self, mock_get_configuration):
        config = MagicMock()
        config.get_questionnaire_description.return_value = {'en': 'foo'}
        config.get_questionnaire_name.return_value = {'en': 'name'}
        mock_get_configuration.return_value = config
        item = self.view.replace_keys(dict(
            name='name', foo='bar', serializer_config='', data={},
            code='sample_1')
        )
        self.assertEqual(
            item['bar'], [{'language': 'en', 'text': 'foo'}]
        )

    def test_language_text_mapping(self):
        data = {'a': 'foo'}
        self.assertEqual(
            self.view.language_text_mapping(**data),
            [{'language': 'a', 'text': 'foo'}]
        )

    @patch.object(QuestionnaireAPIMixin, 'update_dict_keys')
    def test_v1_filter(self, mock_update_dict_keys):
        request = self.factory.get(self.url)
        request.version = 'v1'
        view = self.setup_view(self.view, request, identifier='sample_1')
        view.get(self.request)
        self.assertTrue(mock_update_dict_keys.called)

    @patch.object(QuestionnaireAPIMixin, 'filter_dict')
    def test_v2_filter(self, mock_filter_dict):
        request = self.factory.get(self.url)
        request.version = 'v2'
        view = self.setup_view(self.view, request, identifier='sample_1')
        view.get(self.request)
        self.assertTrue(mock_filter_dict.called)

    def test_api_url_detail_v1(self):
        items = [{'code': 'spam'}]
        updated = list(self.view.filter_dict(items))
        self.assertEqual(
            updated[0]['details'], '/en/api/v1/questionnaires/spam/'
        )

    def test_api_url_detail_v2(self):
        items = [{'code': 'spam'}]
        request = self.request
        request.version = 'v2'
        view = self.setup_view(self.view, request)
        updated = list(view.filter_dict(items))
        self.assertEqual(
            updated[0]['details'], '/en/api/v2/questionnaires/spam/'
        )


class QuestionnaireDetailViewTest(TestCase):
    """
    Tests for v1
    """
    fixtures = ['sample', 'sample_questionnaires']

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.factory = RequestFactory()
        self.url = '/en/api/v1/questionnaires/sample_1/'
        self.request = self.factory.get(self.url)
        self.request.version = 'v1'
        self.invalid_request = self.factory.get('/en/api/v1/questionnaires/foo')
        self.identifier = 'sample_1'
        self.view = self.setup_view(
            QuestionnaireDetailView(), self.request, identifier=self.identifier
        )

    def get_serialized_data(self):
        questionnaire = Questionnaire.objects.get(code=self.identifier)
        return QuestionnaireSerializer(questionnaire).data

    @patch('questionnaire.api.views.get_element')
    def test_access_elasticsearch(self, mock_get_element):
        mock_get_element.return_value = {'oo': 'bar'}
        self.view.get_elasticsearch_item()
        mock_get_element.assert_called_once_with(1, 'sample')

    def test_elasticsearch_error(self):
        with self.assertRaises(Http404):
            self.view.get_elasticsearch_item()

    def test_invalid_element(self):
        with self.assertRaises(Http404):
            self.view.get(self.invalid_request)

    def test_get_object(self):
        item = self.view.get_current_object()
        self.assertEqual(item.id, 1)
        self.assertEqual(item.code, self.identifier)

    def test_get_invalid_object(self):
        with self.assertRaises(Http404):
            self.view.get(self.invalid_request)

    def test_api_detail_url(self):
        item = self.view.replace_keys(self.get_serialized_data())
        with self.assertRaises(KeyError):
            foo = item['api_url']  # noqa

    def test_serialized_item(self):
        with patch.object(QuestionnaireSerializer, 'to_list_values') as values:
            self.view.serialize_item(self.get_serialized_data())
            values.assert_called_once_with(lang='en')

    def test_failed_serialization(self):
        serialized = self.get_serialized_data()
        del serialized['status']
        with self.assertRaises(Http404):
            self.view.serialize_item(serialized)


class ConfiguredQuestionnaireDetailViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = '/en/api/v2/questionnaires/sample_1/'
        self.request = self.factory.get(self.url)
        self.request.version = 'v2'
        self.identifier = 'sample_1'
        self.view = self.setup_view(
            ConfiguredQuestionnaireDetailView(), self.request,
            identifier=self.identifier
        )
        self.view.obj = None

    @patch('questionnaire.api.views.get_language')
    @patch('questionnaire.api.views.get_questionnaire_data_in_single_language')
    def test_prepare_data_one_language(self, mock_single_language,
                                       mock_get_language):
        mock_get_language.return_value = sentinel.language
        mock_serializer = MagicMock(validated_data={
            'data': sentinel.data,
            'original_locale': sentinel.original_locale
        })
        self.view.prepare_data(mock_serializer)
        mock_single_language.assert_called_once_with(
            locale=sentinel.language,
            original_locale=sentinel.original_locale,
            questionnaire_data=sentinel.data
        )

    @patch('questionnaire.api.views.get_questionnaire_data_in_single_language')
    @patch('questionnaire.api.views.ConfiguredQuestionnaire')
    def test_prepare_data(self, mock_conf, mock_single_language):
        mock_single_language.return_value = {}
        self.view.prepare_data(MagicMock())
        self.assertTrue(mock_conf.called)
