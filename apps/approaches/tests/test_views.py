from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from unittest.mock import patch, Mock

from accounts.tests.test_models import create_new_user
from qcat.tests import TestCase
from approaches.views import (
    questionnaire_list,
    questionnaire_list_partial,
)


route_home = 'approaches:home'
route_questionnaire_details = 'approaches:questionnaire_details'
route_questionnaire_list = 'approaches:questionnaire_list'
route_questionnaire_list_partial = 'approaches:questionnaire_list_partial'
route_questionnaire_new = 'approaches:questionnaire_new'
route_questionnaire_new_step = 'approaches:questionnaire_new_step'


def get_valid_details_values():
    return ('foo', 'approaches', 'approaches')


def get_valid_link_form_values():
    args = ('approaches', 'approaches')
    kwargs = {'page_title': 'Approach Links', 'identifier': 'foo'}
    return args, kwargs


def get_valid_new_values():
    args = (
        'approaches', 'approaches/questionnaire/details.html',
        'approaches')
    kwargs = {'identifier': None}
    return args, kwargs


def get_valid_new_step_values():
    args = (get_categories()[0][0], 'approaches', 'approaches')
    kwargs = {'page_title': 'Approaches Form', 'identifier': 'new'}
    return args, kwargs


def get_category_count():
    return len(get_categories())


def get_categories():
    return (
        ('app__1', 'General information'),
        ('app__2', 'Description of the SLM Approach'),
        ('app__3', 'Participation and roles of stakeholders involved'),
        ('app__4', 'Technical support, capacity building, and knowledge '
                   'management'),
        ('app__5', 'Financing and external material support'),
        ('app__6', 'Impact analysis and concluding statements'),
        ('app__7', 'References and links'),
    )


class HomeTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_home)

    @patch('questionnaire.views.advanced_search')
    def test_renders_correct_template(self, mock_advanced_search):
        res = self.client.get(self.url)
        self.assertTemplateUsed(res, 'approaches/questionnaire/list.html')
        self.assertEqual(res.status_code, 200)


class QuestionnaireNewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_questionnaire_new)
        self.request = self.factory.get(self.url)
        self.request.user = create_new_user()
        self.request.session = {}

    def test_questionnaire_new_login_required(self):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')


class QuestionnaireNewStepTest(TestCase):

    fixtures = [
        'groups_permissions.json', 'global_key_values.json',
        'approaches.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(
            route_questionnaire_new_step, kwargs={
                'identifier': 'new', 'step': get_categories()[0][0]})
        self.request = self.factory.get(self.url)
        self.request.user = create_new_user()
        self.request.session = {}

    def test_questionnaire_new_step_login_required(self):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')


class QuestionnaireDetailsTest(TestCase):

    fixtures = [
        'groups_permissions.json', 'global_key_values.json',
        'approaches.json', 'approaches_questionnaires.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(
            route_questionnaire_details, kwargs={'identifier': 'app_1'})

    def test_renders_correct_template(self):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'questionnaire/details.html')
        self.assertEqual(res.status_code, 200)


class QuestionnaireListPartialTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_questionnaire_list_partial)

    @patch('approaches.views.generic_questionnaire_list')
    def test_calls_generic_questionnaire_list(self, mock_questionnaire_list):
        request = self.factory.get(self.url)
        mock_questionnaire_list.return_value = {}
        with self.assertRaises(KeyError):
            questionnaire_list_partial(request)
        mock_questionnaire_list.assert_called_once_with(
            request, 'approaches', template=None)

    @patch('approaches.views.render_to_string')
    @patch('approaches.views.generic_questionnaire_list')
    def test_calls_render_to_string_with_list_template(
            self, mock_questionnaire_list, mock_render_to_string):
        mock_questionnaire_list.return_value = {
            'list_values': 'foo',
            'active_filters': 'bar',
            'count': 0,
        }
        mock_render_to_string.return_value = ''
        self.client.get(self.url)
        mock_render_to_string.assert_any_call(
            'approaches/questionnaire/partial/list.html',
            {'list_values': 'foo'})

    @patch('approaches.views.render_to_string')
    @patch('approaches.views.generic_questionnaire_list')
    def test_calls_render_to_string_with_active_filters(
            self, mock_questionnaire_list, mock_render_to_string):
        mock_questionnaire_list.return_value = {
            'list_values': 'foo',
            'active_filters': 'bar',
            'count': 0,
        }
        mock_render_to_string.return_value = ''
        self.client.get(self.url)
        mock_render_to_string.assert_any_call(
            'active_filters.html', {'active_filters': 'bar'})

    @patch('approaches.views.render_to_string')
    @patch('approaches.views.generic_questionnaire_list')
    def test_calls_render_to_string_with_pagination(
            self, mock_questionnaire_list, mock_render_to_string):
        mock_render_to_string.return_value = ''
        mock_questionnaire_list.return_value = {
            'list_values': 'foo',
            'active_filters': 'bar',
            'count': 0,
        }
        self.client.get(self.url)
        mock_render_to_string.assert_any_call(
            'pagination.html', mock_questionnaire_list.return_value)


class QuestionnaireListTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_questionnaire_list)

    @patch('approaches.views.generic_questionnaire_list')
    def test_calls_generic_function(self, mock_generic_function):
        request = Mock()
        questionnaire_list(request)
        mock_generic_function.assert_called_once_with(
            request, 'approaches',
            template='approaches/questionnaire/list.html',
            filter_url=reverse(route_questionnaire_list_partial))
