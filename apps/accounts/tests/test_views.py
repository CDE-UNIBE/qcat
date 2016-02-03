import json
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test.client import RequestFactory
from qcat.tests import TestCase

from ..forms import WocatAuthenticationForm
from ..tests.test_models import create_new_user
from accounts.views import (
    details,
    questionnaires,
    user_update,
    LoginView)

User = get_user_model()
accounts_route_login = 'login'
accounts_route_logout = 'logout'
accounts_route_welcome = 'welcome'
accounts_route_questionnaires = 'account_questionnaires'
accounts_route_moderation = 'account_moderation'
accounts_route_user = 'user_details'


class LoginViewTest(TestCase):

    def setUp(self):
        self.invalid_login_credentials = {'username': 'foo', 'password': 'bar'}
        self.factory = RequestFactory()
        self.user = create_new_user()

    def test_form_invalid_credentials(self):
        """Invalid data must return a form with errors"""
        response = self.client.post(
            path=reverse('login'),
            data=self.invalid_login_credentials
        )
        self.assertTrue(hasattr(response.context_data['form'], 'errors'))
        self.assertTemplateUsed(response, 'login.html')

    def test_dispatch(self):
        request = self.factory.get(reverse('login'))
        setattr(request, 'user', self.user)
        request.user.is_authenticated = MagicMock(return_value=True)
        view = self.setup_view(LoginView(), request)
        response = view.dispatch(view.request, *view.args, **view.kwargs)
        self.assertEqual(response.status_code, 302)

    @patch('accounts.forms.WocatAuthenticationForm.get_user')
    @patch('accounts.authentication.WocatAuthenticationBackend.authenticate')
    @patch('accounts.client.typo3_client.remote_login')
    @patch('accounts.client.typo3_client.get_user_id')
    @patch('accounts.client.typo3_client.get_and_update_django_user')
    def test_form_valid(self, mock_get_auth_user, mock_auth, mock_remote_login,
                        mock_get_user_id, mock_get_and_update_user):
        # Fake user and required attributes
        user = self.user
        user.backend = 'accounts.authentication.WocatAuthenticationBackend'
        mock_get_auth_user.return_value = user
        mock_auth.return_value = user

        mock_remote_login.return_value = 1
        mock_get_user_id.return_value = 1
        mock_get_and_update_user.return_value = self.user

        form = WocatAuthenticationForm
        form.get_user = lambda x: user
        # Add message store
        request = RequestFactory().post(
            reverse('login'),
            data={'form': form(initial=self.invalid_login_credentials)}
        )
        request.user = user
        request.session = MagicMock()
        request._messages = FallbackStorage

        view = self.setup_view(LoginView(), request)

        response = view.form_valid(form(initial=self.invalid_login_credentials))

        self.assertEqual(request.user, self.user)
        self.assertEqual(response.url, reverse('home'))

    def setup_view(self, view, request, *args, **kwargs):
        """
        Mimic as_view() returned callable, but returns view instance.

        args and kwargs are the same you would pass to ``reverse()``
        """
        view.request = request
        view.args = args
        view.kwargs = kwargs
        return view


class QuestionnairesTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = create_new_user()
        self.url = reverse(
            accounts_route_questionnaires, kwargs={'user_id': 1})
        self.request = self.factory.get(self.url)

    def test_renders_correct_template(self):
        res = self.client.get(self.url)
        self.assertTemplateUsed(res, 'questionnaires.html')

    def test_returns_404_if_user_not_existing(self):
        with self.assertRaises(Http404):
            questionnaires(self.request, -1)

    @patch('accounts.views.generic_questionnaire_list_no_config')
    @patch('accounts.views.get_object_or_404')
    def test_calls_generic_function(
            self, mock_object_or_404, mock_generic_list):
        questionnaires(self.request, 1)
        mock_generic_list.assert_called_once_with(
            self.request, user=mock_object_or_404.return_value)

    @patch('accounts.views.render')
    @patch('accounts.views.generic_questionnaire_list_no_config')
    def test_calls_render(self, mock_generic_list, mock_render):
        questionnaires(self.request, 1)
        mock_render.assert_called_once_with(
            self.request, 'questionnaires.html',
            mock_generic_list.return_value)


class UserUpdateTest(TestCase):

    def setUp(self):
        self.request = RequestFactory().get('/accounts/update')
        self.request.method = 'POST'
        self.request.POST = {'uid': 1}
        self.request.user = create_new_user()

    def test_returns_error_if_no_uid(self):
        self.request.POST = {}
        ret = user_update(self.request)
        json_ret = json.loads(str(ret.content, encoding='utf8'))
        self.assertFalse(json_ret['success'])
        self.assertIn('message', json_ret)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_calls_get_user_information(self, mock_get_user_information):
        mock_get_user_information.return_value = {}
        user_update(self.request)
        mock_get_user_information.assert_called_once_with(1)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_returns_error_if_no_user_info_found(
            self, mock_get_user_information):
        mock_get_user_information.return_value = {}
        ret = user_update(self.request)
        json_ret = json.loads(str(ret.content, encoding='utf8'))
        self.assertFalse(json_ret['success'])
        self.assertIn('message', json_ret)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_creates_user(self, mock_get_user_information):
        self.assertEqual(User.objects.count(), 1)
        mock_get_user_information.return_value = {'username': 'foo@bar.com'}
        user_update(self.request)
        users = User.objects.all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].email, 'foo@bar.com')

    @patch('accounts.client.typo3_client.get_user_information')
    def test_updates_user(self, mock_get_user_information):
        mock_get_user_information.return_value = {
            'username': 'foo@bar.com',
            'first_name': 'Faz',
            'last_name': 'Taz',
        }
        self.request.POST = {'uid': 2}
        user_update(self.request)
        users = User.objects.all()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[1].email, 'foo@bar.com')
        self.assertEqual(users[1].firstname, 'Faz')
        self.assertEqual(users[1].lastname, 'Taz')

    @patch('accounts.client.typo3_client.get_user_information')
    def test_returns_user_name(self, mock_get_user_information):
        mock_get_user_information.return_value = {
            'username': 'foo@bar.com',
            'first_name': 'Faz',
            'last_name': 'Taz',
        }
        ret = user_update(self.request)
        json_ret = json.loads(str(ret.content, encoding='utf8'))
        user = User.objects.get(pk=1)
        self.assertTrue(json_ret['success'])
        self.assertEqual(json_ret['name'], user.get_display_name())


class UserDetailsTest(TestCase):

    def setUp(self):
        self.request = RequestFactory().get('/accounts/user/1')
        self.user = create_new_user()

    @patch('accounts.views.get_object_or_404')
    def test_calls_get_object_or_404(self, mock_get_object_or_404):
        details(self.request, 0)
        mock_get_object_or_404.assert_called_once_with(User, pk=0)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_calls_get_user_information(self, mock_get_user_information):
        mock_get_user_information.return_value = {}
        details(self.request, self.user.id)
        mock_get_user_information.assert_called_once_with(self.user.id)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_updates_user(self, mock_get_user_information):
        mock_get_user_information.return_value = {
            'first_name': 'Faz',
            'last_name': 'Taz',
        }
        details(self.request, self.user.id)
        users = User.objects.all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].email, 'a@b.com')
        self.assertEqual(users[0].firstname, 'Faz')
        self.assertEqual(users[0].lastname, 'Taz')

    @patch('accounts.views.render')
    @patch('accounts.client.typo3_client.get_user_information')
    def test_calls_render(self, mock_get_user_information, mock_render):
        mock_get_user_information.return_value = {}
        details(self.request, self.user.id)
        mock_render.assert_called_once_with(self.request, 'details.html', {
            'detail_user': self.user,
        })
