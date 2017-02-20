from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from unittest.mock import patch

from accounts.tests.test_models import create_new_user
from configuration.configuration import QuestionnaireConfiguration
from qcat.tests import TestCase
from search.views import (
    admin,
    delete_all,
    index,
    search,
    update,
)

route_search_delete_all = 'search:delete_all'
route_search_admin = 'search:admin'
route_search_index = 'search:index'
route_search_search = 'search:search'
route_search_update = 'search:update'


class AdminTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_search_admin)

    def test_login_required(self):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')

    def test_requires_superuser_permissions(self):
        request = self.factory.get(self.url)
        request.user = create_new_user()
        request.session = {}
        with self.assertRaises(PermissionDenied):
            admin(request)

    def test_renders_correct_template(self):
        request = self.factory.get(self.url)
        request.user = create_new_user()
        request.user.is_superuser = True
        request.session = {}
        res = admin(request)
        self.assertEqual(res.status_code, 200)


@patch('search.views.messages')
class IndexTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_search_index, kwargs={'configuration': 'foo'})
        user = create_new_user()
        user.is_superuser = True
        self.request = self.factory.get(self.url)
        self.request.user = user
        self.request.session = {}

    def test_login_required(self, mock_messages):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')

    def test_requires_superuser_permissions(self, mock_messages):
        request = self.factory.get(self.url)
        request.user = create_new_user(id=99, email='foo@bar.com')
        request.session = {}
        with self.assertRaises(PermissionDenied):
            index(request, 'foo')

    @patch('search.views.get_configuration')
    def test_calls_QuestionnaireConfiguration(self, mock_conf, mock_messages):
        index(self.request, 'foo')
        mock_conf.assert_called_once_with('foo')

    @patch('search.views.get_configuration')
    def test_returns_bad_request_if_errors_in_configuration(
            self, mock_conf, mock_messages):
        mock_conf.configuration_error = 'error'
        res = index(self.request, 'foo')
        self.assertEqual(res.status_code, 400)

    @patch('search.views.get_mappings')
    @patch('search.views.create_or_update_index')
    @patch('search.views.get_configuration')
    def test_calls_get_mappings(
            self, mock_conf, mock_create_index, mock_get_mappings,
            mock_messages):
        mock_conf.return_value.get_configuration_errors.return_value = None
        mock_create_index.return_value = None, None, ''
        index(self.request, 'foo')
        mock_get_mappings.assert_called_once_with(mock_conf.return_value)

    @patch('search.views.get_mappings')
    @patch('search.views.create_or_update_index')
    @patch.object(QuestionnaireConfiguration, '__init__')
    @patch.object(QuestionnaireConfiguration, 'get_configuration_errors')
    def test_calls_create_or_update_index(
            self, mock_get_conf_errors, mock_Conf, mock_create_index,
            mock_get_mappings, mock_messages):
        mock_Conf.return_value = None
        mock_get_conf_errors.return_value = None
        mock_create_index.return_value = None, None, ''
        index(self.request, 'foo')
        mock_create_index.assert_called_once_with(
            'foo', mock_get_mappings.return_value)

    @patch('search.views.get_mappings')
    @patch('search.views.create_or_update_index')
    @patch.object(QuestionnaireConfiguration, '__init__')
    @patch.object(QuestionnaireConfiguration, 'get_configuration_errors')
    def test_adds_message_and_redirects_if_not_successful(
            self, mock_get_conf_errors, mock_Conf, mock_create_index,
            mock_get_mappings, mock_messages):
        mock_Conf.return_value = None
        mock_get_conf_errors.return_value = None
        mock_create_index.return_value = None, None, 'error_msg'
        res = index(self.request, 'foo')
        mock_messages.error.assert_called_once_with(
            self.request, 'The following error(s) occured: error_msg')
        self.assertEqual(res.status_code, 302)

    @patch('search.views.get_mappings')
    @patch('search.views.create_or_update_index')
    @patch.object(QuestionnaireConfiguration, '__init__')
    @patch.object(QuestionnaireConfiguration, 'get_configuration_errors')
    def test_adds_message_and_redirects_if_successful(
            self, mock_get_conf_errors, mock_Conf, mock_create_index,
            mock_get_mappings, mock_messages):
        mock_Conf.return_value = None
        mock_get_conf_errors.return_value = None
        mock_create_index.return_value = True, None, ''
        res = index(self.request, 'foo')
        mock_messages.success.assert_called_once_with(
            self.request, 'Index "foo" was created or updated.')
        self.assertEqual(res.status_code, 302)


@patch('search.views.messages')
class UpdateTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(
            route_search_update, kwargs={'configuration': 'foo'})
        user = create_new_user()
        user.is_superuser = True
        self.request = self.factory.get(self.url)
        self.request.user = user
        self.request.session = {}

    def test_login_required(self, mock_messages):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')

    def test_requires_superuser_permissions(self, mock_messages):
        request = self.factory.get(self.url)
        request.user = create_new_user(id=99, email='foo@bar.com')
        request.session = {}
        with self.assertRaises(PermissionDenied):
            update(request, 'foo')

    @patch('search.views.get_configuration')
    def test_calls_get_configuration(self, mock_conf, mock_messages):
        update(self.request, 'foo')
        mock_conf.assert_called_once_with('foo')

    @patch('search.views.get_configuration')
    def test_returns_bad_request_if_errors_in_configuration(
            self, mock_conf, mock_messages):
        mock_conf.configuration_error = 'error'
        res = update(self.request, 'foo')
        self.assertEqual(res.status_code, 400)

    @patch('search.views.put_questionnaire_data')
    @patch.object(QuestionnaireConfiguration, '__init__')
    @patch.object(QuestionnaireConfiguration, 'get_configuration_errors')
    def test_calls_put_questionnaire_data(
            self, mock_get_conf_errors, mock_Conf, mock_put_questionnaire_data,
            mock_messages):
        mock_Conf.return_value = None
        mock_get_conf_errors.return_value = None
        mock_put_questionnaire_data.return_value = None, []
        update(self.request, 'foo')
        self.assertEqual(mock_put_questionnaire_data.call_count, 1)

    @patch('search.views.put_questionnaire_data')
    @patch.object(QuestionnaireConfiguration, '__init__')
    @patch.object(QuestionnaireConfiguration, 'get_configuration_errors')
    def test_adds_message_and_redirects_if_not_successful(
            self, mock_get_conf_errors, mock_Conf, mock_put_questionnaire_data,
            mock_messages):
        mock_Conf.return_value = None
        mock_get_conf_errors.return_value = None
        mock_put_questionnaire_data.return_value = None, ['error_msg']
        res = update(self.request, 'foo')
        mock_messages.error.assert_called_once_with(
            self.request, 'The following error(s) occured: error_msg')
        self.assertEqual(res.status_code, 302)

    @patch('search.views.put_questionnaire_data')
    @patch.object(QuestionnaireConfiguration, '__init__')
    @patch.object(QuestionnaireConfiguration, 'get_configuration_errors')
    def test_adds_message_and_redirects_if_successful(
            self, mock_get_conf_errors, mock_Conf, mock_put_questionnaire_data,
            mock_messages):
        mock_Conf.return_value = None
        mock_get_conf_errors.return_value = None
        mock_put_questionnaire_data.return_value = 0, []
        res = update(self.request, 'foo')
        mock_messages.success.assert_called_once_with(
            self.request,
            '0 Questionnaires of configuration "foo" successfully indexed.')
        self.assertEqual(res.status_code, 302)


@patch('search.views.messages')
class DeleteTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_search_delete_all)
        user = create_new_user()
        user.is_superuser = True
        self.request = self.factory.get(self.url)
        self.request.user = user
        self.request.session = {}

    def test_login_required(self, mock_messages):
        res = self.client.get(self.url, follow=True)
        self.assertTemplateUsed(res, 'login.html')

    def test_requires_superuser_permissions(self, mock_messages):
        request = self.factory.get(self.url)
        request.user = create_new_user(id=99, email='foo@bar.com')
        request.session = {}
        with self.assertRaises(PermissionDenied):
            delete_all(request)

    @patch('search.views.delete_all_indices')
    def test_calls_delete_all_indices(
            self, mock_delete_all_indices, mock_messages):
        mock_delete_all_indices.return_value = True, ''
        delete_all(self.request)
        mock_delete_all_indices.assert_called_once_with()

    @patch('search.views.delete_all_indices')
    def test_adds_message_and_redirects_if_not_successful(
            self, mock_delete_all_indices, mock_messages):
        mock_delete_all_indices.return_value = False, 'foo'
        res = delete_all(self.request)
        mock_messages.error.assert_called_once_with(
            self.request, 'The following error(s) occured: foo')
        self.assertEqual(res.status_code, 302)

    @patch('search.views.delete_all_indices')
    def test_adds_message_and_redirects_if_successful(
            self, mock_delete_all_indices, mock_messages):
        mock_delete_all_indices.return_value = True, ''
        res = delete_all(self.request)
        mock_messages.success.assert_called_once_with(
            self.request, 'All indices successfully deleted.')
        self.assertEqual(res.status_code, 302)


class SearchTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(route_search_search)

    @patch('search.views.simple_search')
    def test_calls_simple_search(self, mock_simple_search):
        self.client.get(self.url)
        mock_simple_search.assert_called_once_with('')

    @patch('search.views.simple_search')
    def test_calls_simple_search_with_get_param(self, mock_simple_search):
        request = self.factory.get(self.url)
        request.user = create_new_user()
        request.GET = {'q': 'foo'}
        search(request)
        mock_simple_search.assert_called_once_with('foo')

    def test_renders_correct_template(self):
        res = self.client.get(self.url)
        self.assertTemplateUsed(res, 'sample/questionnaire/list.html')
        self.assertEqual(res.status_code, 200)
