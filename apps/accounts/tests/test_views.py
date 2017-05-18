import json
from unittest.mock import patch, MagicMock

from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.test import override_settings
from django.test.client import RequestFactory

from qcat.tests import TestCase
from questionnaire.models import Questionnaire

from ..forms import WocatAuthenticationForm
from ..tests.test_models import create_new_user
from accounts.views import (
    user_update,
    LoginView,
    ProfileView, QuestionnaireStatusListView,
    UserDetailView, QuestionnaireSearchView)

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
        self.factory.GET = MagicMock()
        self.user = create_new_user()
        self.view = self.setup_view(view=LoginView(), request=self.factory)

    def setup_view(self, view, request, *args, **kwargs):
        """
        Mimic as_view() returned callable, but returns view instance.

        args and kwargs are the same you would pass to ``reverse()``
        """
        view.request = request
        view.args = args
        view.kwargs = kwargs
        return view

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

    @override_settings(USE_NEW_WOCAT_AUTHENTICATION=False)
    def test_form_invalid_old_auth_backend(self):
        response = self.view.form_invalid(form=None)
        self.assertIsInstance(response, TemplateResponse)

    @override_settings(USE_NEW_WOCAT_AUTHENTICATION=True)
    def test_form_invalid_new_auth_backend_unkknown_user(self):
        form = MagicMock(cleaned_data={'username': 'foo'})
        response = self.view.form_invalid(form)
        self.assertIsInstance(response, TemplateResponse)

    @override_settings(USE_NEW_WOCAT_AUTHENTICATION=True)
    @patch('accounts.client.typo3_client.get_user_information')
    def test_form_invalid_new_auth_backend_unkknown_api_user(self, mock_get_info):
        form = MagicMock(cleaned_data={'username': 'a@b.com'})
        response = self.view.form_invalid(form)
        self.assertIsInstance(response, TemplateResponse)
        mock_get_info.assert_called_once_with(1)

    @override_settings(
        USE_NEW_WOCAT_AUTHENTICATION=True,
        REACTIVATE_WOCAT_ACCOUNT_URL='42'
    )
    @patch('accounts.client.typo3_client.get_user_information')
    def test_form_invalid_new_auth_backend_known_user(self, mock_get_info):
        form = MagicMock(cleaned_data={'username': 'a@b.com'})
        mock_get_info.return_value = {'is_active': True}
        response = self.view.form_invalid(form)
        self.assertIsInstance(response, TemplateResponse)
        form = MagicMock(cleaned_data={'username': 'a@b.com'})
        mock_get_info.return_value = {'is_active': False}
        response = self.view.form_invalid(form)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, '42')


class ProfileViewTest(TestCase):
    fixtures = ['sample_global_key_values.json', 'sample.json', 'sample_questionnaires.json']

    def setUp(self):
        self.factory = RequestFactory()
        view = ProfileView()
        self.request = self.factory.get(reverse('account_questionnaires'))
        self.user = create_new_user()
        self.request.user = self.user
        self.view = self.setup_view(view, self.request)

    def create_questionnaire(self, status, user=None):
        Questionnaire.create_new(
            configuration_code='sample',
            data={'foo': 'bar'},
            user=user or self.user,
            status=status
        )

    def test_renders_correct_template(self):
        self.assertEqual(self.view.get_template_names(), ['questionnaires.html'])

    @patch('accounts.views.query_questionnaires')
    def test_get_questionnaires(self, mock_query_questionnaires):
        self.view.get(self.request)
        mock_query_questionnaires.assert_called_once_with(
            configuration_code='all', limit=None, only_current=False, request=self.request
        )

    def test_user_required(self):
        self.assertTrue(issubclass(ProfileView, LoginRequiredMixin))

    def test_get_status_list_only_public(self):
        status_list = self.view.get_status_list()
        self.assertDictEqual(status_list, {4: 'Public'})

    def test_get_status_list_own_questionnaire(self):
        self.create_questionnaire(2)
        status_list = self.view.get_status_list()
        self.assertDictEqual(status_list, {2: 'Submitted', 4: 'Public'})

    def test_get_status_list_other_questionnaire(self):
        self.create_questionnaire(3, user=create_new_user(id=2, email='c@d.com'))
        status_list = self.view.get_status_list()
        self.assertDictEqual(status_list, {4: 'Public'})

    def test_get_status_list_other_questionnaire_with_permissions(self):
        self.create_questionnaire(3, user=create_new_user(id=3, email='d@e.com'))
        status_list = self.view.get_status_list()
        self.assertDictEqual(status_list, {4: 'Public'})
        # add permission group, pseudo wocat-secretariat.
        self.request.user.get_all_permissions = lambda : ['questionnaire.publish_questionnaire']
        status_list = self.view.get_status_list()
        self.assertDictEqual(status_list, {3: 'Reviewed', 4: 'Public'})


class QuestionnaireStatusListViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        view = QuestionnaireStatusListView()
        self.request = self.factory.get(reverse('questionnaires_status_list'))
        self.user = create_new_user()
        self.request.user = self.user
        self.view = self.setup_view(view, self.request)
        self.valid_request = self.factory.get('{}?status={}'.format(
            reverse('questionnaires_status_list'),
            settings.QUESTIONNAIRE_PUBLIC
        ))
        self.valid_request.user = self.user

    def _get_valid_view(self):
        return self.setup_view(QuestionnaireStatusListView(), self.valid_request)

    def test_user_required(self):
        self.assertTrue(issubclass(ProfileView, LoginRequiredMixin))

    def test_get_no_status(self):
        with self.assertRaises(Http404):
            self.view.status

    def test_get_invalid_status(self):
        request = self.factory.get('?status=12345'.format(
            reverse('questionnaires_status_list')
        ))
        view = self.setup_view(QuestionnaireStatusListView(), request)
        with self.assertRaises(Http404):
            view.status

    def test_get_valid_status(self):
        view = self.setup_view(QuestionnaireStatusListView(), self.valid_request)
        self.assertEqual(view.status, settings.QUESTIONNAIRE_PUBLIC)

    @patch('accounts.views.query_questionnaires')
    def test_get_queryset(self, mock_query_questionnaires):
        self._get_valid_view().get_queryset()
        mock_query_questionnaires.assert_called_once_with(
            configuration_code='all', limit=None, only_current=False,
            request=self.valid_request, user=self.user
        )

    def test_get_filter_user(self):
        filter = self._get_valid_view().get_filter_user()
        self.assertDictEqual(filter, {'user': self.user})

    def test_get_filter_user_non_public(self):
        request = self.factory.get('{}?status={}'.format(
            reverse('questionnaires_status_list'),
            settings.QUESTIONNAIRE_SUBMITTED
        ))
        view = self.setup_view(QuestionnaireStatusListView(), request)
        filter = view.get_filter_user()
        self.assertDictEqual(filter, {'user': None})

    @patch('accounts.views.get_list_values')
    def test_get_context_data(self, mock_get_list_values):
        view = self.setup_view(QuestionnaireStatusListView(), self.valid_request)
        view.object_list = []
        view.get_context_data()
        self.assertTrue(mock_get_list_values.called)


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

    @patch('accounts.client.Typo3Client.get_user_information')
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
        self.user = create_new_user()
        self.request = RequestFactory().get(reverse('user_details', kwargs={'pk': self.user.id}))
        self.view = self.setup_view(UserDetailView(), request=self.request, pk=self.user.id)

    def test_raise_404(self):
        request = RequestFactory().get(reverse('user_details', kwargs={'pk': 123}))
        view = self.setup_view(UserDetailView(), request=request, pk=123)
        with self.assertRaises(Http404):
            view.get(self.request)

    @patch('accounts.client.typo3_client.get_user_information')
    @patch('accounts.client.typo3_client.update_user')
    def test_returns_user(self, mock_update_user, mock_get_information):
        mock_get_information.return_value = []
        self.assertEqual(self.view.get_object(), self.user)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_calls_get_user_information(self, mock_get_user_information):
        mock_get_user_information.return_value = {}
        self.view.get_object()
        mock_get_user_information.assert_called_once_with(self.user.id)

    @patch('accounts.client.typo3_client.get_user_information')
    def test_updates_user(self, mock_get_user_information):
        mock_get_user_information.return_value = {
            'first_name': 'Faz',
            'last_name': 'Taz',
        }
        self.view.get_object()
        users = User.objects.all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].email, 'a@b.com')
        self.assertEqual(users[0].firstname, 'Faz')
        self.assertEqual(users[0].lastname, 'Taz')

    def test_get_unccd_countries(self):
        self.view.object = MagicMock()
        get_unccd_countries = MagicMock(return_value=[])
        self.view.object.get_unccd_countries = get_unccd_countries
        self.view.get_context_data()
        get_unccd_countries.assert_called_once_with()


class QuestionnaireSearchViewTest(TestCase):

    def setUp(self):
        self.user = MagicMock()
        self.user.is_staff = True
        self.url = reverse('staff_questionnaires_search')
        self.request = RequestFactory().get(self.url)
        self.request.user = self.user
        self.view = self.setup_view(QuestionnaireSearchView(), request=self.request)

    def test_dispatch(self):
        response = self.view.dispatch(request=self.request)
        self.assertTrue(isinstance(response, TemplateResponse))

    def test_dispatch_non_staff(self):
        request = RequestFactory().get(self.url)
        request.user = MagicMock()
        request.user.is_staff = False
        view = self.setup_view(QuestionnaireSearchView(), request=request)
        with self.assertRaises(Http404):
            view.dispatch(request=request)

    def test_get(self):
        self.request.is_ajax = lambda : True
        view = self.setup_view(self.view, self.request)
        with patch.object(QuestionnaireSearchView, 'get_json_data') as mock_json:
            response = view.get(request=self.request)
            self.assertTrue(isinstance(response, JsonResponse))
            mock_json.assert_called_once()

    def test_pagination(self):
        self.request.is_ajax = MagicMock()
        self.view.get_paginate_by(None)
        self.request.is_ajax.assert_called_once()

    @patch.object(QuestionnaireSearchView, 'get_queryset')
    def test_get_json_data(self, mock_get_queryset):
        mock_get_queryset.return_value = [MagicMock()]
        json = list(self.view.get_json_data())
        self.assertListEqual(
            ['name', 'url', 'compilers', 'country', 'status', 'id'],
            list(json[0].keys())
        )
