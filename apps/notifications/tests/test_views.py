import logging
from unittest import mock
from unittest.mock import call

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import RequestFactory

from braces.views import LoginRequiredMixin
from django.test import override_settings
from model_mommy import mommy
from notifications.models import Log, StatusUpdate, MemberUpdate, ReadLog, \
    ActionContextQuerySet
from notifications.views import LogListView, LogCountView, ReadLogUpdateView, \
    LogQuestionnairesListView, LogInformationUpdateCreateView, \
    LogSubscriptionPreferencesView, SignedLogSubscriptionPreferencesView
from qcat.tests import TestCase


class LogListViewTest(TestCase):

    def setUp(self):
        self.view = LogListView()
        self.url_path = reverse('notification_partial_list')
        self.request = RequestFactory().get(self.url_path)
        self.user = {}
        self.request.user = self.user
        self.view_instance = self.setup_view(
            view=self.view, request=self.request
        )
        member_add_log = mommy.make(
            model=Log,
            id=8,
            action=settings.NOTIFICATIONS_ADD_MEMBER
        )
        self.change_log = mommy.make(
            model=Log,
            id=42,
            action=settings.NOTIFICATIONS_CHANGE_STATUS
        )
        mommy.make(model=StatusUpdate, log=self.change_log)
        mommy.make(model=MemberUpdate, log=member_add_log)

    def get_view_with_get_querystring(self, param):
        request = RequestFactory().get(
            '{url}?{param}'.format(url=self.url_path, param=param)
        )
        request.user = self.user
        return self.setup_view(view=self.view, request=request)

    def test_force_login(self):
        self.assertIsInstance(self.view_instance, LoginRequiredMixin)

    def test_queryset_method(self):
        self.assertEqual(
            self.view_instance.queryset_method,
            'user_log_list'
        )

    def test_queryset_method_pending(self):
        self.assertEqual(
            self.get_view_with_get_querystring('is_pending').queryset_method,
            'user_pending_list'
        )

    def test_get_paginate_by(self):
        self.assertEqual(
            self.view_instance.get_paginate_by(None),
            settings.NOTIFICATIONS_LIST_PAGINATE_BY
        )

    def test_get_paginate_by_teaser(self):
        self.assertEqual(
            self.get_view_with_get_querystring('is_teaser').get_paginate_by(None),
            settings.NOTIFICATIONS_TEASER_PAGINATE_BY
        )

    @mock.patch('notifications.views.Log.actions.user_log_list')
    def test_get_queryset(self, mock_actions):
        self.view_instance.get_queryset()
        mock_actions.assert_called_once_with(user={})

    @mock.patch('notifications.views.Log.actions.user_pending_list')
    def test_get_queryset_pending(self, mock_actions):
        self.get_view_with_get_querystring('is_pending').get_queryset()
        mock_actions.assert_called_once_with(user={})

    @mock.patch.object(LogListView, 'add_user_aware_data')
    def test_get_context_data_logs(self, mock_add_user_aware_data):
        self.view_instance.object_list = 'foo'
        self.view_instance.get_context_data()
        mock_add_user_aware_data.assert_called_once_with('foo')

    def _test_add_user_aware_data(self):
        # for faster tests, mock all the elements. elements are created here
        # as this makes the tests more readable.
        pth = 'notifications.views.Log.actions'
        with mock.patch('{}.read_id_list'.format(pth)) as read_id_list:
            read_id_list.return_value = [42]
            with mock.patch('{}.user_pending_list'.format(pth)) as pending:
                pending.values_list.return_value = [8, 42]
                logs = Log.objects.all()
                return list(self.view_instance.add_user_aware_data(logs))

    def test_add_user_aware_data_keys(self):
        data_keys = self._test_add_user_aware_data()[0].keys()
        for key in ['id', 'created', 'text', 'is_read', 'is_todo', 'edit_url']:
            self.assertTrue(key in data_keys)

    def test_add_user_aware_data_is_read(self):
        data = self._test_add_user_aware_data()
        # logs are ordered by creation date -  42 is the newer one
        self.assertTrue(data[0]['is_read'])

    def test_add_user_aware_data_is_not_read(self):
        data = self._test_add_user_aware_data()
        self.assertFalse(data[1]['is_read'])

    #def test_add_user_aware_data_is_todo(self):
    #    data = self._test_add_user_aware_data()
    #    self.assertTrue(data[1]['is_todo'])

    def test_add_user_aware_data_is_not_todo(self):
        data = self._test_add_user_aware_data()
        self.assertFalse(data[0]['is_todo'])

    @override_settings(NOTIFICATIONS_ACTIONS={'foo': 'bar', 'result': '42'})
    def test_statuses_in_context(self):
        self.view_instance.object_list = []
        context = self.view_instance.get_context_data()
        self.assertDictEqual(
            context['statuses'],
            {'foo': 'bar', 'result': '42'}
        )

    @mock.patch('notifications.views.Log.actions.user_log_list')
    def test_status_filter_queryset(self, mock_user_log_list):
        mock_user_log_list.return_value = []
        self.assertEqual(
            [], self.view_instance.get_queryset()
        )

    @mock.patch('notifications.views.Log.actions.user_log_list')
    def test_status_filter_queryset_for_status(self, mock_user_log_list):
        mock_user_log_list.return_value = Log.objects.filter()
        view = self.view
        view.get_statuses = mock.MagicMock(return_value=[3])
        view_instance = self.setup_view(
            view=view, request=self.request
        )
        self.assertQuerysetEqual(
            view_instance.get_queryset(),
            [self.change_log.id],
            transform=lambda item: item.id
        )

    def test_get_status_invalid(self):
        request = RequestFactory().get('{}?statuses=foo'.format(self.url_path))
        view = self.setup_view(self.view, request)
        self.assertEqual(view.get_statuses(), [])

    @override_settings(NOTIFICATIONS_ACTIONS={'2': 'bar'})
    def test_get_status_invalid_config(self):
        request = RequestFactory().get('{}?statuses=1'.format(self.url_path))
        view = self.setup_view(self.view, request)
        self.assertEqual(view.get_statuses(), [])

    def test_get_status_valid(self):
        request = RequestFactory().get('{}?statuses=1,2,3'.format(self.url_path))
        view = self.setup_view(self.view, request)
        self.assertEqual(view.get_statuses(), [1, 2, 3])


class ReadLogUpdateViewTest(TestCase):

    def setUp(self):
        self.view = ReadLogUpdateView()
        self.request = RequestFactory().post(
            reverse('notification_read'),
            data={'user': 123, 'log': 'log', 'checked': 'true'}
        )
        self.user = mock.MagicMock(id=123)
        self.request.user = self.user
        self.view_instance = self.setup_view(view=self.view, request=self.request)

    def test_validate_data_all_keys(self):
        self.assertFalse(
            self.view_instance.validate_data()
        )

    def test_validate_data_id_type(self):
        self.assertFalse(
            self.view_instance.validate_data(checked='1', log='1', user='foo')
        )

    def test_validate_data_invalid_user(self):
        self.assertFalse(
            self.view_instance.validate_data(checked='456', log='1', user='456')
        )

    def test_validate_data_valid(self):
        self.assertTrue(
            self.view_instance.validate_data(checked='1', log='1', user='123')
        )

    @mock.patch('notifications.views.ReadLog.objects.update_or_create')
    def test_post_valid_checked(self, mock_get_or_create):
        self.view_instance.post(request=self.request)
        mock_get_or_create.assert_called_once_with(
            user_id='123', log_id='log', defaults={'is_read': True}
        )

    @mock.patch('notifications.views.ReadLog.objects.update_or_create')
    def test_post_valid_unchecked(self, mock_get_or_create):
        request = RequestFactory().post(
            reverse('notification_read'),
            data={'user': 123, 'log': 'log', 'checked': 'false'}
        )
        self.view_instance.post(request=request)
        mock_get_or_create.assert_called_once_with(
            user_id='123', log_id='log', defaults={'is_read': False}
        )

    @mock.patch.object(ReadLogUpdateView, 'validate_data')
    def test_post_invalid(self, mock_validate_data):
        logging.disable(logging.CRITICAL)
        mock_validate_data.return_value = False
        with self.assertRaises(Http404):
            self.view_instance.post(request=self.request)


class LogCountViewTest(TestCase):

    def setUp(self):
        super().setUp()
        self.request = RequestFactory().get(reverse('notification_new_count'))
        self.request.user = mommy.make(get_user_model())
        self.view = self.setup_view(view=LogCountView(), request=self.request)
        mommy.make(
            model=Log,
            catalyst=self.request.user,
            action=settings.NOTIFICATIONS_CHANGE_STATUS,
            _quantity=4
        )
        mommy.make(
            model=Log,
            catalyst=self.request.user,
            action=settings.NOTIFICATIONS_EDIT_CONTENT,
            _quantity=2
        )

    @mock.patch('notifications.views.Log.actions.only_unread_logs')
    def test_get_unread_only(self, mock_only_unread_logs):
        self.view.get(request=self.request)
        mock_only_unread_logs.assert_called_once_with(
            user=self.request.user
        )

    def test_log_count(self):
        response = self.view.get(request=self.request)
        self.assertEqual(response.content, b'4')

    def test_log_count_one_read(self):
        mommy.make(
            model=ReadLog,
            log=Log.objects.filter(action=settings.NOTIFICATIONS_CHANGE_STATUS).first(),
            user=self.request.user,
            is_read=True
        )
        response = self.view.get(request=self.request)
        self.assertEqual(response.content, b'3')


class LogQuestionnairesListViewTest(TestCase):

    def setUp(self):
        super().setUp()
        self.request = RequestFactory().get(reverse('notification_questionnaire_logs'))
        self.request.user = 'foo'
        self.view = self.setup_view(view=LogQuestionnairesListView(), request=self.request)

    @mock.patch.object(ActionContextQuerySet, 'user_log_list')
    def test_get_questionnaire_logs(self, mock_user_log_list):
        self.view.get_questionnaire_logs('foo')
        mock_user_log_list.assert_called_once_with(user='foo')


    @mock.patch.object(LogQuestionnairesListView, 'get_questionnaire_logs')
    def test_get(self, mock_get_questionnaire_logs):
        mock_get_questionnaire_logs.return_value = ['foo_1', 'foo_2', 'bar_3']
        response = self.view.get(self.request)
        self.assertEqual(
            response.content, b'{"questionnaires": ["bar_3", "foo_1", "foo_2"]}'
        )


class LogInformationUpdateCreateViewTest(TestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('notification_inform_compiler')
        self.view = LogInformationUpdateCreateView()
        self.request = RequestFactory().get(self.url)
        self.request.user = 'foo'
        self.view = self.setup_view(view=self.view, request=self.request)

    def test_get_compiler_query(self):
        questionnaire = mock.MagicMock()
        self.view.get_compiler(questionnaire)
        self.assertEqual(
            questionnaire.method_calls[0],
            call.questionnairemembership_set.get(role='compiler')
        )

    def test_get_compiler(self):
        sentinel = mock.sentinel
        questionnaire = mock.MagicMock()
        questionnaire.questionnairemembership_set.get.return_value = sentinel
        self.assertEqual(
            self.view.get_compiler(questionnaire),
            sentinel.user
        )

    @mock.patch('notifications.views.query_questionnaire')
    def test_get_questionnaire(self, mock_query_questionnaire):
        one_questionnaire = mock.MagicMock()
        one_questionnaire.first = lambda : 'foo'
        mock_query_questionnaire.return_value = one_questionnaire
        self.assertEqual(
            self.view.get_questionnaire('foo'), 'foo'
        )

    @mock.patch('notifications.views.query_questionnaire')
    def test_get_questionnaire_raises(self, mock_query_questionnaire):
        not_exists = mock.MagicMock()
        not_exists.exists = lambda : False
        mock_query_questionnaire.return_value = not_exists
        with self.assertRaises(Http404):
            self.view.get_questionnaire('foo')

    @mock.patch('notifications.views.query_questionnaire')
    def test_get_questionnaire_calls_filter(self, mock_query_questionnaire):
        self.view.get_questionnaire('foo')
        mock_query_questionnaire.assert_called_once_with(
            identifier='foo', request=self.request
        )

    @override_settings(NOTIFICATIONS_FINISH_EDITING='setting')
    @mock.patch.object(LogInformationUpdateCreateView, 'get_questionnaire')
    @mock.patch.object(LogInformationUpdateCreateView, 'get_compiler')
    def test_post(self, mock_get_compiler, mock_get_questionnaire):
        compiler = mock.MagicMock()
        mock_get_questionnaire.return_value = mock.sentinel.questionnaire
        mock_get_compiler.return_value = compiler
        request = RequestFactory().post(self.url, data={
            'identifier': 'foo',
            'message': 'bar'
        })
        with mock.patch('notifications.views.InformationLog') as mock_create:
            self.setup_view(view=self.view, request=self.request).post(request)
            mock_create.assert_called_once_with(
                action='setting',
                questionnaire=mock.sentinel.questionnaire,
                receiver=compiler,
                sender='foo'
            )


class LogSubscriptionPreferencesMixinTest(TestCase):

    def setUp(self):
        self.url = reverse('notification_preferences')
        self.view = LogSubscriptionPreferencesView()
        self.request = RequestFactory().get(self.url)
        self.user = mommy.make(get_user_model())
        self.obj = self.user.mailpreferences
        self.request.user = self.user
        self.request._messages = mock.MagicMock()
        self.view = self.setup_view(view=self.view, request=self.request)
        self.view.object = self.obj

    def test_get_initial(self):
        self.obj.wanted_actions = 'some,thing,yay'
        self.assertEqual(
            ['some', 'thing', 'yay'],
            self.view.get_initial()['wanted_actions']
        )

    def test_get_form_valid_changed_language(self):
        self.view.object = mock.MagicMock()
        self.view.object.has_changed_language = False
        form = mock.MagicMock()
        form.changed_data = ['language']
        self.view.form_valid(form)
        self.assertTrue(self.view.object.has_changed_language)

    def test_get_form_valid_message(self):
        self.view.form_valid(mock.MagicMock())
        self.assertTrue(self.request._messages.method_calls)


class SignedLogSubscriptionPreferencesViewTest(TestCase):

    def setUp(self):
        self.user = mommy.make(get_user_model())
        self.obj = self.user.mailpreferences
        self.view = SignedLogSubscriptionPreferencesView()
        self.request = RequestFactory().get(str(self.obj.get_signed_url()))
        self.request._messages = mock.MagicMock()
        self.view = self.setup_view(view=self.view, request=self.request)
        self.view.object = self.obj

    def test_get_success_url_signed(self):
        self.request.user = mock.MagicMock
        self.request.user.is_authenticated = lambda: False
        self.assertEqual(
            self.view.get_success_url(),
            self.obj.get_signed_url()
        )

    def test_get_success_url_user(self):
        self.request.user = self.user
        self.request.user.is_authenticated = lambda: True
        self.assertEqual(
            self.view.get_success_url(),
            reverse('notification_preferences')
        )

    def test_get_object_user(self):
        self.request.user = self.user
        self.request.user.is_authenticated = lambda: True
        self.assertEqual(
            self.view.get_object(),
            self.obj
        )

    def test_get_signed_object(self):
        self.request.user = mock.MagicMock()
        self.request.user.is_authenticated = lambda: False
        self.view.kwargs['token'] = mock.MagicMock()
        with mock.patch.object(Signer, 'unsign') as mock_unsign:
            mock_unsign.return_value = self.obj.id
            self.assertEqual(
                self.view.get_object(), self.obj
            )
            mock_unsign.assert_called_with(self.view.kwargs['token'])

    def test_get_signed_object_404(self):
        self.request.user = mock.MagicMock()
        self.request.user.is_authenticated = lambda: False
        self.view.kwargs['token'] = mock.MagicMock()
        with self.assertRaises(Http404):
            self.view.get_object()
