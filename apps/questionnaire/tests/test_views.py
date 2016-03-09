import json
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http.response import HttpResponse
from django.test.client import RequestFactory
from unittest.mock import patch, Mock

from accounts.tests.test_models import create_new_user
from configuration.configuration import (
    QuestionnaireConfiguration,
    QuestionnaireCategory,
    QuestionnaireSection,
)
from qcat.tests import TestCase
from questionnaire.models import Questionnaire, File
from questionnaire.views import (
    generic_file_upload,
    generic_questionnaire_details,
    generic_questionnaire_link_form,
    generic_questionnaire_link_search,
    generic_questionnaire_list,
    generic_questionnaire_new,
    generic_questionnaire_new_step,
)
from questionnaire.tests.test_view_utils import get_valid_pagination_parameters
from sample.tests.test_views import (
    get_section_count,
    get_valid_new_step_values,
    get_valid_new_values,
    get_valid_details_values,
    get_valid_list_values,
    get_valid_link_form_values,
    route_questionnaire_details,
    route_questionnaire_list,
    route_questionnaire_link_search,
)

file_upload_route = 'file_upload'
file_display_route = 'file_serve'
valid_file = 'static/assets/img/img01.jpg'
invalid_file = 'bower.json'  # Needs to exist but not valid file type


class GenericQuestionnaireLinkFormTest(TestCase):

    fixtures = [
        'groups_permissions.json', 'sample_global_key_values.json',
        'sample.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.url = '/sample/edit/links'
        self.request = self.factory.get(self.url)
        self.request.user = create_new_user()
        self.request.session = {}

    def test_requires_login(self):
        self.client.logout()
        res = self.client.post(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')

    @patch('questionnaire.views.get_configuration')
    def test_calls_get_configuration(self, mock_get_configuration):
        generic_questionnaire_link_form(
            self.request, *get_valid_link_form_values()[0],
            **get_valid_link_form_values()[1])
        mock_get_configuration.assert_called_once_with('sample')

    @patch.object(QuestionnaireConfiguration, 'get_links_configuration')
    @patch.object(QuestionnaireConfiguration, '__init__')
    def test_calls_get_links_configuration(
            self, mock_QuestionnaireConfiguration,
            mock_get_links_configuration):
        mock_QuestionnaireConfiguration.return_value = None
        mock_get_links_configuration.return_value \
            = []
        generic_questionnaire_link_form(
            self.request, *get_valid_link_form_values()[0],
            **get_valid_link_form_values()[1])
        mock_get_links_configuration.assert_called_once_with()

    @patch('questionnaire.views.get_session_questionnaire')
    def test_calls_get_session_questionnaire(
            self, mock_get_session_questionnaire):
        mock_get_session_questionnaire.return_value = {}
        generic_questionnaire_link_form(
            self.request, *get_valid_link_form_values()[0],
            **get_valid_link_form_values()[1])
        mock_get_session_questionnaire.assert_called_once_with(
            self.request, 'sample', 'foo')

    @patch('questionnaire.views.render')
    def test_calls_render(self, mock_render):
        generic_questionnaire_link_form(
            self.request, *get_valid_link_form_values()[0],
            **get_valid_link_form_values()[1])
        mock_render.assert_called_once_with(
            self.request,
            [
                'form/links/sample.html',
                'form/links/default.html',
            ],
            {
                'valid': True,
                'overview_url': '/en/sample/edit/foo/#links',
                'link_forms': [(
                    {
                        'label': '',
                        'keyword': 'samplemulti',
                        'search_url': '/en/samplemulti/search/links/',
                    }, []
                )],
                'configuration_name': 'sample',
                'title': 'SAMPLE Links'
            }
        )


class GenericQuestionnaireLinkSearchTest(TestCase):

    fixtures = [
        'sample_global_key_values.json', 'sample.json',
        'sample_questionnaires.json']

    @patch('questionnaire.views.get_configuration')
    def test_calls_get_configuration(self, mock_get_configuration):
        mock = Mock()
        mock.get_name_keywords.return_value = None, None
        mock_get_configuration.return_value = mock
        generic_questionnaire_link_search(Mock(), 'sample')
        mock_get_configuration.assert_called_once_with('sample')

    @patch('questionnaire.views.get_configuration')
    @patch('questionnaire.views.query_questionnaires_for_link')
    def test_calls_query_questionnaires_for_link(
            self, mock_query, mock_get_configuration):
        mock_get_configuration.get_list_data.return_value = []
        mock_query.return_value = 0, []
        mock_request = Mock()
        generic_questionnaire_link_search(mock_request, 'sample')
        mock_query.assert_called_once_with(
            mock_request, mock_get_configuration(), mock_request.GET.get())

    def test_returns_empty_if_no_q(self):
        req = RequestFactory().get(reverse(route_questionnaire_link_search))
        ret = generic_questionnaire_link_search(req, 'sample')
        j = json.loads(ret.content.decode('utf-8'))
        self.assertEqual(j, {})

    def test_returns_empty_if_no_results(self):
        req = RequestFactory().get(reverse(route_questionnaire_link_search))
        req.GET = {'q': 'foo'}
        user = Mock()
        user.is_authenticated.return_value = False
        req.user = user
        ret = generic_questionnaire_link_search(req, 'sample')
        j = json.loads(ret.content.decode('utf-8'))
        self.assertEqual(j, {"total": 0, "data": []})

    def test_returns_results(self):
        req = RequestFactory().get(reverse(route_questionnaire_link_search))
        req.GET = {'q': 'key'}
        user = Mock()
        user.is_authenticated.return_value = False
        req.user = user
        ret = generic_questionnaire_link_search(req, 'sample')
        j = json.loads(ret.content.decode('utf-8'))
        self.assertEqual(j.get('total'), 2)
        data = j.get('data')
        self.assertEqual(len(data), 2)
        self.assertEqual(len(data[0]), 5)
        self.assertEqual(data[0].get('code'), 'sample_1')
        self.assertIn('display', data[0])
        self.assertEqual(data[0].get('id'), 1)
        self.assertEqual(data[0].get('name'), 'Sample Key 1a')
        self.assertEqual(data[0].get('value'), 1)
        self.assertEqual(len(data[1]), 5)
        self.assertEqual(data[1].get('code'), 'sample_2')
        self.assertIn('display', data[1])
        self.assertEqual(data[1].get('id'), 2)
        self.assertEqual(data[1].get('name'), 'Sample Key 1b')
        self.assertEqual(data[1].get('value'), 2)


class GenericQuestionnaireNewStepTest(TestCase):

    fixtures = [
        'groups_permissions.json', 'sample_global_key_values.json',
        'sample.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/sample/new/cat_1')
        self.request.user = create_new_user()
        self.request.session = {}

    @patch('questionnaire.views.get_configuration')
    def test_calls_get_configuration(self, mock_get_configuration):
        mock_get_configuration.return_value.get_category.return_value.\
            get_form.return_value = {}, []
        generic_questionnaire_new_step(
            self.request, *get_valid_new_step_values()[0])
        mock_get_configuration.assert_called_once_with('sample')

    @patch.object(QuestionnaireConfiguration, 'get_category')
    def test_gets_category(self, mock_get_category):
        mock_get_category.return_value = None
        with self.assertRaises(Http404):
            generic_questionnaire_new_step(
                self.request, 'cat_1', 'sample', 'template', 'route')
        mock_get_category.assert_called_once_with('cat_1')

    @patch('questionnaire.views.get_session_questionnaire')
    def test_calls_get_session_questionnaire(
            self, mock_get_session_questionnaire):
        mock_get_session_questionnaire.return_value = {}
        generic_questionnaire_new_step(
            self.request, *get_valid_new_step_values()[0])
        mock_get_session_questionnaire.assert_called_once_with(
            self.request, 'sample', None)

    @patch('questionnaire.views.get_questionnaire_data_for_translation_form')
    def test_calls_get_questionnaire_data_for_translation_form(
            self, mock_get_questionnaire_data):
        generic_questionnaire_new_step(
            self.request, *get_valid_new_step_values()[0])
        mock_get_questionnaire_data.assert_called_once_with({}, 'en', None)

    @patch.object(QuestionnaireCategory, 'get_form')
    def test_calls_category_get_form(self, mock_get_form):
        mock_get_form.return_value = {}, None
        generic_questionnaire_new_step(
            self.request, *get_valid_new_step_values()[0])
        mock_get_form.assert_called_once_with(
            post_data=None, show_translation=False, initial_data={},
            edit_mode='edit', edited_questiongroups=[])

    @patch.object(messages, 'success')
    @patch.object(QuestionnaireCategory, 'get_form')
    @patch('questionnaire.views.save_session_questionnaire')
    def test_form_submission_saves_form(
            self, mock_save_session_questionnaire, mock_get_form,
            mock_messages):
        mock_get_form.return_value = None, []
        r = self.request
        r.method = 'POST'
        generic_questionnaire_new_step(
            r, *get_valid_new_step_values()[0])
        mock_save_session_questionnaire.assert_called_once_with(
            self.request, 'sample', None, questionnaire_data={},
            questionnaire_links={}, edited_questiongroups=[])

    @patch.object(QuestionnaireCategory, 'get_form')
    @patch('questionnaire.views.render')
    def test_calls_render(self, mock_render, mock_get_form):
        mock_get_form.return_value = {}, "bar"
        generic_questionnaire_new_step(
            self.request, *get_valid_new_step_values()[0])
        mock_render.assert_called_once_with(
            self.request, 'form/category.html', {
                'category_formsets': "bar",
                'category_config': {},
                'title': 'QCAT Form',
                'overview_url': '/en/sample/edit/new/#cat_0',
                'valid': True,
                'configuration_name': 'sample',
                'edit_mode': 'edit',
                'view_url': '',
            })

    def test_returns_rendered_response(self):
        ret = generic_questionnaire_new_step(
            self.request, *get_valid_new_step_values()[0])
        self.assertIsInstance(ret, HttpResponse)


class GenericQuestionnaireNewTest(TestCase):

    fixtures = [
        'groups_permissions.json', 'sample_global_key_values.json',
        'sample.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/sample/new')
        self.request.user = create_new_user()
        self.request.session = {}

    @patch('questionnaire.views.get_configuration')
    def test_calls_get_configuration(self, mock_get_configuration):
        generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        mock_get_configuration.assert_called_once_with('sample')

    @patch('questionnaire.views.get_session_questionnaire')
    def test_calls_get_session_questionnaire(
            self, mock_get_session_questionnaire):
        mock_get_session_questionnaire.return_value = {}
        generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        mock_get_session_questionnaire.assert_called_once_with(
            self.request, 'sample', 'new')

    @patch('questionnaire.views.get_configuration')
    @patch('questionnaire.views.clean_questionnaire_data')
    def test_calls_clean_questionnaire_data(
            self, mock_clean_questionnaire_data, mock_get_configuration):
        mock_clean_questionnaire_data.return_value = {"foo": "bar"}, []
        r = self.request
        r.method = 'POST'
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_clean_questionnaire_data.assert_called_once_with(
            {}, mock_get_configuration())

    @patch.object(messages, 'info')
    def test_adds_message_if_empty(self, mock_messages_info):
        r = self.request
        r.method = 'POST'
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_messages_info.assert_called_once_with(
            r, 'You cannot submit an empty questionnaire',
            fail_silently=True)

    @patch('questionnaire.views.redirect')
    def test_redirects_to_same_path_if_empty(self, mock_redirect):
        r = self.request
        r.method = 'POST'
        r.path = 'foo'
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_redirect.assert_called_once_with('foo')

    @patch.object(Questionnaire, 'create_new')
    @patch('questionnaire.views.clean_questionnaire_data')
    def test_calls_create_new_questionnaire(
            self, mock_clean_questionnaire_data, mock_create_new):
        r = self.request
        r.method = 'POST'
        mock_clean_questionnaire_data.return_value = {"foo": "bar"}, []
        mock_create_new.return_value = Mock()
        mock_create_new.return_value.code = 'foo'
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_create_new.assert_called_once_with(
            'sample', {}, self.request.user, previous_version=None,
            old_data=None)

    @patch('questionnaire.views.clear_session_questionnaire')
    @patch('questionnaire.views.clean_questionnaire_data')
    def test_calls_clear_session_questionnaire(
            self, mock_clean_questionnaire_data,
            mock_clear_session_questionnaire):
        r = self.request
        r.method = 'POST'
        mock_clean_questionnaire_data.return_value = {"foo": "bar"}, []
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_clear_session_questionnaire.assert_called_once_with(
            self.request, 'sample', 'new')

    @patch.object(messages, 'success')
    @patch('questionnaire.views.clean_questionnaire_data')
    def test_adds_message(
            self, mock_clean_questionnaire_data, mock_messages_sucess):
        r = self.request
        r.method = 'POST'
        mock_clean_questionnaire_data.return_value = {"foo": "bar"}, []
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_messages_sucess.assert_called_once_with(
            r, 'The questionnaire was successfully created.',
            fail_silently=True)

    @patch('questionnaire.views.redirect')
    @patch.object(Questionnaire, 'create_new')
    @patch('questionnaire.views.clean_questionnaire_data')
    def test_redirects_to_success_route(
            self, mock_clean_questionnaire_data,
            mock_create_new, mock_redirect):
        r = self.request
        r.method = 'POST'
        mock_clean_questionnaire_data.return_value = {"foo": "bar"}, []
        mock_create_new.return_value = Mock()
        mock_create_new.return_value.code = 'foo'
        generic_questionnaire_new(
            r, *get_valid_new_values()[0], **get_valid_new_values()[1])
        mock_redirect.assert_called_once_with('/en/sample/view/foo/#top')

    @patch('questionnaire.views.get_questionnaire_data_in_single_language')
    def test_calls_get_questionnaire_data_in_single_language(
            self, mock_get_questionnaire_data):
        generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        mock_get_questionnaire_data.assert_called_once_with({}, 'en')

    @patch.object(QuestionnaireConfiguration, 'get_details')
    def test_calls_get_details(self, mock_get_details):
        generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        mock_get_details.assert_called_once_with(
            {}, permissions=['edit_questionnaire'],
            edit_step_route='sample:questionnaire_new_step',
            questionnaire_object=None, csrf_token=None,
            edited_questiongroups=[], view_mode='edit')

    @patch('questionnaire.views.get_list_values')
    @patch('questionnaire.views.Questionnaire')
    def test_calls_get_list_values(
            self, mock_Questionnaire, mock_get_list_values):
        link = Mock()
        mock_Questionnaire.objects.filter.return_value = [link]
        generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        mock_get_list_values.assert_called_once_with(
            questionnaire_objects=[link], with_links=False,
            configuration_code=link.configurations.first().code)

    @patch.object(QuestionnaireConfiguration, 'get_filter_configuration')
    @patch.object(QuestionnaireSection, 'get_details')
    @patch('questionnaire.views.render')
    def test_calls_render(
            self, mock_render, mock_get_details, mock_filter_configuration):
        mock_get_details.return_value = "foo"
        generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        mock_render.assert_called_once_with(
            self.request, 'sample/questionnaire/details.html', {
                'questionnaire_identifier': 'new',
                'sections': ["foo"] * get_section_count(),
                'images': [],
                'links': {},
                'filter_configuration': mock_filter_configuration.return_value,
                'permissions': ['edit_questionnaire'],
                'edited_questiongroups': [],
                'view_mode': 'edit',
                'is_blocked': None,
            })

    def test_returns_rendered_response(self):
        ret = generic_questionnaire_new(
            self.request, *get_valid_new_values()[0],
            **get_valid_new_values()[1])
        self.assertIsInstance(ret, HttpResponse)


@patch('questionnaire.views.render')
class GenericQuestionnaireDetailsTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get(reverse(
            route_questionnaire_details, args=[1]))
        self.request.user = Mock()
        self.request.user.is_authenticated.return_value = False

    @patch('questionnaire.views.query_questionnaire')
    def test_calls_query_questionnaire(
            self, mock_query_questionnaire, mock_render):
        mock_query_questionnaire.return_value.first.return_value = None
        with self.assertRaises(Http404):
            generic_questionnaire_details(
                self.request, *get_valid_details_values())
        mock_query_questionnaire.assert_called_once_with(self.request, 'foo')

    @patch('questionnaire.views.query_questionnaire')
    @patch('questionnaire.views.get_configuration')
    def test_calls_get_configuration(
            self, mock_get_configuration, mock_query_questionnaire,
            mock_render):
        mock_query_questionnaire.return_value.first.return_value.data = {}
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_get_configuration.assert_called_once_with('sample')

    @patch('questionnaire.views.get_questionnaire_data_in_single_language')
    @patch('questionnaire.views.query_questionnaire')
    @patch('questionnaire.views.get_configuration')
    def test_calls_get_questionnaire_data_in_single_language(
            self, mock_conf, mock_query_questionnaire,
            mock_get_q_data_in_single_lang, mock_render):
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_get_q_data_in_single_lang.assert_called_once_with(
            mock_query_questionnaire.return_value.first.return_value.data,
            'en')

    @patch('questionnaire.views.handle_review_actions')
    @patch('questionnaire.views.redirect')
    @patch('questionnaire.views.get_questionnaire_data_in_single_language')
    @patch('questionnaire.views.query_questionnaire')
    @patch('questionnaire.views.get_configuration')
    def test_calls_handle_review_actions_if_post_values(
            self, mock_conf, mock_query_questionnaire,
            mock_get_q_data_in_single_lang, mock_redirect,
            mock_handle_review_actions, mock_render):
        self.request.method = 'POST'
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_handle_review_actions.assert_called_once_with(
            self.request,
            mock_query_questionnaire.return_value.first.return_value, 'sample')

    @patch('questionnaire.views.redirect')
    @patch('questionnaire.views.get_questionnaire_data_in_single_language')
    @patch('questionnaire.views.query_questionnaire')
    @patch('questionnaire.views.get_configuration')
    def test_calls_redirect_if_post_values(
            self, mock_conf, mock_query_questionnaire,
            mock_get_q_data_in_single_lang, mock_redirect, mock_render):
        self.request.method = 'POST'
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_redirect.assert_called_once_with(
            'sample:questionnaire_details',
            mock_query_questionnaire.return_value.first.return_value.code)

    @patch('questionnaire.views.get_query_status_filter')
    @patch.object(QuestionnaireConfiguration, 'get_details')
    @patch('questionnaire.views.query_questionnaire')
    def test_calls_get_details(
            self, mock_query_questionnaire, mock_get_details,
            mock_get_query_status_filter, mock_render):
        mock_query_questionnaire.return_value.first.return_value.data = {}
        mock_q_obj = mock_query_questionnaire.return_value.first.return_value
        self.request.user.is_authenticated.return_value = True
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_get_details.assert_called_once_with(
            data={},
            questionnaire_object=mock_q_obj,
            review_config={
                'review_status': mock_q_obj.status,
                'csrf_token_value': None,
                'permissions': mock_q_obj.get_permissions.return_value,
            },
            permissions=mock_q_obj.get_permissions.return_value)

    @patch('questionnaire.views.get_configuration')
    @patch('questionnaire.views.query_questionnaire')
    def test_calls_get_image_data(
            self, mock_query_questionnaire, mock_conf, mock_render):
        mock_query_questionnaire.return_value.first.return_value.data = {}
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_conf.return_value.get_image_data.assert_called_once_with({})

    @patch('questionnaire.views.get_configuration')
    @patch('questionnaire.views.get_list_values')
    @patch('questionnaire.views.query_questionnaire')
    def test_calls_get_list_values(
            self, mock_query_questionnaire, mock_get_list_values, mock_conf,
            mock_render):
        q = Mock()
        q.data = {}
        link = Mock()
        q.links.filter.return_value = [link]
        q.members.all.return_value = []
        mock_query_questionnaire.return_value.first.return_value = q
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mock_get_list_values.assert_called_once_with(
            questionnaire_objects=[link], with_links=False,
            configuration_code=link.configurations.first().code)

    @patch('questionnaire.views.get_configuration')
    @patch('questionnaire.views.query_questionnaire')
    def test_calls_render(
            self, mock_query_questionnaire, mock_conf, mock_render):
        mock_q_obj = mock_query_questionnaire.return_value.first.return_value
        mock_q_obj.data = {}
        generic_questionnaire_details(
            self.request, *get_valid_details_values())
        mfc = mock_conf.return_value.get_filter_configuration.return_value
        img = mock_conf.return_value.get_image_data.return_value
        mock_render.assert_called_once_with(
            self.request, 'sample/questionnaire/details.html', {
                'sections': mock_conf.return_value.get_details.return_value,
                'questionnaire_identifier': 'foo',
                'images': img.get.return_value,
                'links': {},
                'filter_configuration': mfc,
                'permissions': mock_q_obj.get_permissions.return_value,
                'view_mode': 'view',
            })


@patch('questionnaire.views.render')
@patch('questionnaire.views.advanced_search')
class GenericQuestionnaireListTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get(reverse(route_questionnaire_list))
        self.request.user = Mock()
        self.request.user.get_all_permissions.return_value = []

    @patch('questionnaire.views.get_configuration')
    def test_calls_get_configuration(
            self, mock_get_configuration, mock_advanced_search, mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_configuration.assert_called_once_with('sample')

    @patch('questionnaire.views.get_active_filters')
    @patch('questionnaire.views.get_configuration')
    def test_calls_get_active_filters(
            self, mock_conf, mock_get_active_filters, mock_advanced_search,
            mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_active_filters.assert_called_once_with(
            mock_conf.return_value, self.request.GET)

    @patch('questionnaire.views.get_limit_parameter')
    def test_calls_get_limit_parameter(
            self, mock_get_limit_parameter, mock_advanced_search, mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_limit_parameter.assert_called_once_with(self.request)

    @patch('questionnaire.views.get_page_parameter')
    def test_calls_get_page_parameter(
            self, mock_get_page_parameter, mock_advanced_search, mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_page_parameter.assert_called_once_with(self.request)

    @patch('questionnaire.views.query_questionnaires')
    def test_db_query_calls_query_questionnaires(
            self, mock_query_questionnaires, mock_advanced_search,
            mock_render):
        mock_query_questionnaires.return_value = []
        generic_questionnaire_list(self.request, 'sample', db_query=True)
        mock_query_questionnaires.assert_called_once_with(
            self.request, 'sample', only_current=False, limit=None)

    @patch('questionnaire.views.get_pagination_parameters')
    @patch('questionnaire.views.get_list_values')
    @patch('questionnaire.views.query_questionnaires')
    @patch('questionnaire.views.get_paginator')
    def test_db_query_calls_get_paginator(
            self, mock_get_paginator, mock_query_questionnaires,
            mock_get_list_values, mock_get_pagination_parameters,
            mock_advanced_search, mock_render):
        mock_query_questionnaires.return_value = []
        mock_get_paginator.return_value = None, None
        generic_questionnaire_list(self.request, 'sample', db_query=True)
        mock_get_paginator.assert_called_once_with([], 1, 10)

    @patch('questionnaire.views.get_list_values')
    def test_db_query_calls_get_list_values(
            self, mock_get_list_values, mock_advanced_search, mock_render):
        self.request.user = Mock()
        self.request.user.is_authenticated.return_value = False
        generic_questionnaire_list(self.request, 'sample', db_query=True)
        self.assertEqual(mock_get_list_values.call_count, 1)

    @patch('questionnaire.views.get_configuration_index_filter')
    def test_es_calls_get_configuration_index_filter(
            self, mock_get_configuration_index_filter, mock_advanced_search,
            mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_configuration_index_filter.assert_called_once_with(
            'sample', only_current=False)

    def test_es_calls_advanced_search(self, mock_advanced_search, mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_advanced_search.assert_called_once_with(
            filter_params=[], query_string='', configuration_codes=['sample'],
            limit=10, offset=0)

    @patch('questionnaire.views.get_pagination_parameters')
    @patch('questionnaire.views.get_list_values')
    @patch('questionnaire.views.get_paginator')
    @patch('questionnaire.views.ESPagination')
    def test_es_creates_esPagination(
            self, mock_ESPagination, mock_get_paginator, mock_get_list_values,
            mock_get_pagination_parameters, mock_advanced_search, mock_render):
        mock_get_paginator.return_value = None, None
        generic_questionnaire_list(self.request, *get_valid_list_values())
        self.assertEqual(mock_ESPagination.call_count, 1)

    @patch('questionnaire.views.get_list_values')
    def test_es_calls_get_list_values(
            self, mock_get_list_values, mock_advanced_search, mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        self.assertEqual(mock_get_list_values.call_count, 1)

    @patch.object(QuestionnaireConfiguration, 'get_filter_configuration')
    def test_calls_get_filter_configuration(
            self, mock_get_filter_configuration, mock_advanced_search,
            mock_render):
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_filter_configuration.assert_called_once_with()

    @patch('questionnaire.views.get_list_values')
    @patch('questionnaire.views.get_paginator')
    @patch('questionnaire.views.get_pagination_parameters')
    def test_calls_get_pagination_parameters(
            self, mock_get_pagination_parameters, mock_get_paginator,
            mock_get_list_values, mock_advanced_search, mock_render):
        mock_get_paginator.return_value = None, None
        generic_questionnaire_list(self.request, *get_valid_list_values())
        mock_get_pagination_parameters.assert_called_once_with(
            self.request, None, None)

    @patch('questionnaire.views.get_configuration')
    def test_calls_render(
            self, mock_conf, mock_advanced_search, mock_render):
        mock_advanced_search.return_value = {}
        generic_questionnaire_list(self.request, *get_valid_list_values())
        ret = {
            'list_values': [],
            'filter_configuration':
                mock_conf.return_value.get_filter_configuration
                                      .return_value,
            'filter_url': '',
            'active_filters': [],
        }
        ret.update(get_valid_pagination_parameters())
        mock_render.assert_called_once_with(
            self.request, 'sample/questionnaire/list.html', ret)

    def test_returns_only_template_values_if_no_template(
            self, mock_advanced_search, mock_render):
        ret = generic_questionnaire_list(self.request, 'sample', template=None)
        self.assertIsInstance(ret, dict)


class GenericFileUploadTest(TestCase):

    fixtures = ['groups_permissions.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(file_upload_route)
        self.request = self.factory.post(self.url)
        self.request.user = create_new_user()
        self.request.session = {}
        self.mock_request = Mock()
        self.mock_request.method = 'POST'
        self.mock_request.session = {}
        self.mock_request.user = self.request.user
        self.mock_request.FILES.getlist.return_value = [Mock()]

    def test_upload_login_required(self):
        self.client.logout()
        res = self.client.post(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')

    def test_upload_only_post_allowed(self):
        res = generic_file_upload(self.request)
        self.assertEqual(res.status_code, 400)

    def test_handles_post_without_files(self):
        res = generic_file_upload(self.request)
        self.assertEqual(res.status_code, 400)
        content = json.loads(res.content.decode('utf-8'))
        self.assertFalse(content.get('success'))

    @patch.object(File, 'get_data')
    @patch.object(File, 'handle_upload')
    def test_calls_handle_upload(self, mock_handle_upload, mock_get_data):
        mock_get_data.return_value = {}
        generic_file_upload(self.mock_request)
        mock_handle_upload.assert_called_once()

    def test_handles_exception_by_handle_upload(self):
        res = generic_file_upload(self.request)
        self.assertEqual(res.status_code, 400)
        content = json.loads(res.content.decode('utf-8'))
        self.assertFalse(content.get('success'))

    @patch.object(File, 'get_data')
    @patch.object(File, 'handle_upload')
    def test_calls_get_data(self, mock_handle_upload, mock_get_data):
        mock_get_data.return_value = {}
        generic_file_upload(self.mock_request)
        mock_get_data.assert_called_once_with(
            file_object=mock_handle_upload.return_value)


class GenericFileServeTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.file = File.create_new('image/jpeg')
        self.url = reverse(
            file_display_route, args=('display', self.file.uuid))
        self.request = self.factory.get(self.url)

    def test_raises_404_if_invalid_action(self):
        url = reverse(file_display_route, args=('foo', 'uid'))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_raises_404_if_file_not_found(self):
        url = reverse(file_display_route, args=('display', 'uid'))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    @patch.object(File, 'get_data')
    def test_calls_get_data(self, mock_get_data):
        self.client.get(self.url)
        mock_get_data.assert_called_once_with(file_object=self.file)

    @patch('questionnaire.views.retrieve_file')
    def test_calls_retrieve_file(self, mock_retrieve_file):
        self.client.get(self.url)
        mock_retrieve_file.assert_called_once_with(self.file, thumbnail=None)

    @patch('questionnaire.views.retrieve_file')
    def test_calls_retrieve_file_with_thumbnail(self, mock_retrieve_file):
        self.client.get(self.url + '?format=foo')
        mock_retrieve_file.assert_called_once_with(self.file, thumbnail='foo')

    @patch('questionnaire.views.retrieve_file')
    def test_returns_file(self, mock_retrieve_file):
        mock_retrieve_file.return_value = ('file', 'filename')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    @patch('questionnaire.views.retrieve_file')
    def test_returns_file_download(self, mock_retrieve_file):
        url = reverse(file_display_route, args=('download', self.file.uuid))
        mock_retrieve_file.return_value = ('file', 'filename')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
