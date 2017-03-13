from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from unittest.mock import patch, Mock

from accounts.tests.test_models import create_new_user
from qcat.tests import TestCase
from samplemulti.views import (
    home,
    questionnaire_list,
    questionnaire_list_partial,
)

route_questionnaire_details = 'samplemulti:questionnaire_details'
route_home = 'samplemulti:home'
route_questionnaire_link_search = 'samplemulti:questionnaire_link_search'
route_questionnaire_list = 'samplemulti:questionnaire_list'
route_questionnaire_list_partial = 'samplemulti:questionnaire_list_partial'
route_questionnaire_new = 'samplemulti:questionnaire_new'
route_questionnaire_new_step = 'samplemulti:questionnaire_new_step'


def get_valid_link_form_values():
    args = ('samplemulti', 'samplemulti')
    kwargs = {'page_title': 'SAMPLEMULTI Links', 'identifier': 'foo'}
    return args, kwargs


def get_valid_new_step_values():
    args = (get_categories()[0][0], 'samplemulti', 'samplemulti')
    kwargs = {'page_title': 'SAMPLEMULTI Form', 'identifier': 'new'}
    return args, kwargs


def get_valid_new_values():
    args = (
        'samplemulti', 'questionnaire/details.html', 'samplemulti')
    kwargs = {'identifier': None}
    return args, kwargs


def get_valid_details_values():
    return ('foo', 'samplemulti', 'samplemulti')


def get_valid_list_values():
    return ('samplemulti', 'samplemulti/questionnaire/list.html')


def get_category_count():
    return len(get_categories())


def get_section_count():
    return len(get_sections())


def get_categories():
    return (
        ('mcat_1', 'MCategory 1'),
    )


def get_sections():
    return (
        ('msection_1', 'MSection 1'),
    )


def get_position_of_category(category, start0=False):
    for i, cat in enumerate(get_categories()):
        if cat[0] == category:
            if start0 is True:
                return i
            else:
                return i + 1
    return None


class SampleMultiHomeTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_home)

    @patch('samplemulti.views.generic_questionnaire_list')
    def test_calls_generic_questionnaire_list(self, mock_questionnaire_list):
        request = self.factory.get(self.url)
        request.user = create_new_user()
        home(request)
        mock_questionnaire_list.assert_called_once_with(
            request, 'samplemulti', template=None, only_current=True, limit=3,
        )

    @patch('samplemulti.views.generic_questionnaire_list')
    def test_renders_correct_template(self, mock_questionnaire_list):
        mock_questionnaire_list.return_value = {}
        res = self.client.get(self.url)
        self.assertTemplateUsed(res, 'samplemulti/home.html')
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
        'samplemulti.json']

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
        'groups_permissions.json', 'samplemulti.json',
        'samplemulti_questionnaires.json']

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(
            route_questionnaire_details, kwargs={
                'identifier': 'samplemulti_1'})

    def test_renders_correct_template(self):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'questionnaire/details.html')
        self.assertEqual(res.status_code, 200)

    # @patch('samplemulti.views.generic_questionnaire_details')
    # def test_calls_generic_function(self, mock_questionnaire_details):
    #     request = self.factory.get(self.url)
    #     questionnaire_details(request, 'foo')
    #     mock_questionnaire_details.assert_called_once_with(
    #         request, *get_valid_details_values())


class QuestionnaireListPartialTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_questionnaire_list_partial)

    @patch('samplemulti.views.generic_questionnaire_list')
    def test_calls_generic_questionnaire_list(self, mock_questionnaire_list):
        request = self.factory.get(self.url)
        mock_questionnaire_list.return_value = {}
        with self.assertRaises(KeyError):
            questionnaire_list_partial(request)
        mock_questionnaire_list.assert_called_once_with(
            request, 'samplemulti', template=None)

    @patch('samplemulti.views.render_to_string')
    @patch('samplemulti.views.generic_questionnaire_list')
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
            'samplemulti/questionnaire/partial/list.html',
            {'list_values': 'foo'})

    @patch('samplemulti.views.render_to_string')
    @patch('samplemulti.views.generic_questionnaire_list')
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

    @patch('samplemulti.views.render_to_string')
    @patch('samplemulti.views.generic_questionnaire_list')
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

    @patch('samplemulti.views.generic_questionnaire_list')
    def test_calls_generic_function(self, mock_generic_function):
        request = Mock()
        questionnaire_list(request)
        mock_generic_function.assert_called_once_with(
            request, 'samplemulti',
            template='samplemulti/questionnaire/list.html',
            filter_url='/en/samplemulti/list_partial/')
