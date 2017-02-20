from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from unittest.mock import patch, Mock

from qcat.tests import TestCase
from wocat.views import (
    questionnaire_list,
    questionnaire_list_partial,
    HomeView)


route_home = 'wocat:home'
route_questionnaire_list = 'wocat:questionnaire_list'
route_questionnaire_list_partial = 'wocat:questionnaire_list_partial'


def get_valid_details_values():
    return (1, 'wocat', 'wocat', 'wocat/questionnaire/details.html')


def get_valid_list_values():
    return ('wocat', 'wocat/questionnaire/list.html')


class WocatHomeTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_home)

    def setup_view(self, view, request, *args, **kwargs):
        """Mimic ``as_view()``, but returns view instance.
        Use this function to get view instances on which you can run unit tests,
        by testing specific methods."""

        view.request = request
        view.args = args
        view.kwargs = kwargs
        return view

    @patch.object(HomeView, 'get_context_data')
    def test_renders_correct_template(self, mock_ctx_data):
        mock_ctx_data.return_value = {}
        res = self.client.get(self.url)
        self.assertTemplateUsed(res, 'wocat/home.html')
        self.assertEqual(res.status_code, 200)


class QuestionnaireListPartialTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_questionnaire_list_partial)

    @patch('wocat.views.generic_questionnaire_list')
    def test_calls_generic_questionnaire_list(self, mock_questionnaire_list):
        request = self.factory.get(self.url)
        mock_questionnaire_list.return_value = {}
        with self.assertRaises(KeyError):
            questionnaire_list_partial(request)
        mock_questionnaire_list.assert_called_once_with(
            request, 'wocat', template=None)

    @patch('wocat.views.render_to_string')
    @patch('wocat.views.generic_questionnaire_list')
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
            'wocat/questionnaire/partial/list.html',
            {'list_values': 'foo'})

    @patch('wocat.views.render_to_string')
    @patch('wocat.views.generic_questionnaire_list')
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

    @patch('wocat.views.render_to_string')
    @patch('wocat.views.generic_questionnaire_list')
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

    @patch('wocat.views.generic_questionnaire_list')
    def test_calls_generic_function(self, mock_generic_function):
        request = Mock()
        questionnaire_list(request)
        mock_generic_function.assert_called_once_with(
            request, 'wocat', template='wocat/questionnaire/list.html',
            filter_url='/en/wocat/list_partial/')
