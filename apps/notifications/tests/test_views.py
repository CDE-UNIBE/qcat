from unittest import mock

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import RequestFactory

from braces.views import LoginRequiredMixin
from model_mommy import mommy
from notifications.models import Log
from notifications.views import LogListView, LogCountView, ReadLogUpdateView
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
        mommy.make(model=Log, id=8)
        mommy.make(model=Log, id=42)

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

    def test_get_context_data_path(self):
        self.view_instance.object_list = 'foo'
        context = self.view_instance.get_context_data()
        self.assertEqual(
            context['path'], '{}?page='.format(self.url_path)
        )

    def test_get_context_data_path_pending(self):
        view = self.get_view_with_get_querystring('is_pending')
        view.object_list = ''
        context = view.get_context_data()
        self.assertEqual(
            context['path'], '{}?is_pending=True&page='.format(self.url_path)
        )

    def test_get_context_data_path_teaser(self):
        view = self.get_view_with_get_querystring('is_teaser')
        view.object_list = ''
        context = view.get_context_data()
        self.assertEqual(
            context['path'], '{}?is_teaser=True&page='.format(self.url_path)
        )

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
        mock_validate_data.return_value = False
        with self.assertRaises(Http404):
            self.view_instance.post(request=self.request)



class LogCountViewTest(TestCase):

    @mock.patch('notifications.views.Log.actions.user_log_count')
    def test_get(self, mock_user_log_count):
        mock_user_log_count.return_value = '123'
        request = RequestFactory().get(reverse('notification_new_count'))
        request.user = {}
        view = self.setup_view(view=LogCountView(), request=request)
        response = view.get(request=request)
        self.assertEqual(
            response.content, b'123'
        )