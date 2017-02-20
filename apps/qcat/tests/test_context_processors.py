from datetime import timedelta
from unittest.mock import MagicMock, patch, mock_open, sentinel, call

from django.conf import settings
from django.test import override_settings
from django.utils.timezone import now

from qcat.context_processors import template_settings, MaintenanceAnnouncement
from qcat.tests import TestCase


class QcatContextProcessor(TestCase):

    @override_settings(WARN_HEADER='mind the gap')
    def test_settings_variable_in_context(self):
        ctx = template_settings(MagicMock())
        self.assertEquals(
            ctx['WARN_HEADER'], 'mind the gap'
        )

    @patch('qcat.context_processors.MaintenanceAnnouncement')
    def test_announce_deployment(self, mock_announcement):
        mock_announcement.return_value.overlay = {'my_overlay': 'important'}
        ctx = template_settings(MagicMock())
        self.assertEquals(ctx['my_overlay'], 'important')


class MaintenanceAnnouncementTest(TestCase):

    def setUp(self):
        self.when = (now() + timedelta(seconds=settings.DEPLOY_TIMEOUT)).isoformat()
        self.request = MagicMock(session={'saw_deploy_warning': ''})

    @patch.object(MaintenanceAnnouncement, 'get_next_maintenance')
    def test_init(self, next_maintenance):
        next_maintenance.return_value = False
        announcement = MaintenanceAnnouncement
        announcement.flush_maintenance_time = MagicMock()
        self.assertEqual(announcement(MagicMock()).overlay, {})
        self.assertFalse(announcement.flush_maintenance_time.called)

    @patch('qcat.context_processors.cache')
    def test_get_next_maintenance_anonymous(self, mock_cache):
        request = MagicMock()
        request.user.is_authenticated = MagicMock(return_value=False)
        announcement = MaintenanceAnnouncement(request)
        self.assertDictEqual(announcement.overlay, {})
        self.assertFalse(mock_cache.called)

    @patch('qcat.context_processors.cache')
    @patch('qcat.context_processors.messages')
    def test_next_maintenance_access_cache(self, mock_messages, mock_cache):
        mock_cache.get = MagicMock(return_value=self.when)
        MaintenanceAnnouncement(self.request)
        self.assertEquals(len(mock_cache.method_calls), 1)

    @patch('qcat.context_processors.cache')
    def test_flush_cache(self, mock_cache):
        mock_cache.get = MagicMock(return_value=None)
        mock_cache.set = MagicMock(return_value=None)
        MaintenanceAnnouncement(self.request)
        mock_cache.set.assert_called_once_with(
            key='next_maintenance',
            timeout=MaintenanceAnnouncement.file_read_timeout,
            value=''
        )

    @override_settings(CACHES={'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
    })
    def test_flush_file(self,):
        f = MagicMock()
        with patch('qcat.context_processors.open', mock_open(mock=f)):
            MaintenanceAnnouncement(self.request).flush_maintenance_time()
            # this is not nice, but seems the most obvious
            self.assertIn(call().flush(), f._mock_mock_calls)

    @patch('qcat.context_processors.messages')
    def test_set_display_warning(self, mock_messages):
        MaintenanceAnnouncement(MagicMock()).set_display_deploy_warning('')
        self.assertEqual(
            len(mock_messages.method_calls), 1
        )

    @patch('qcat.context_processors.cache')
    @patch('qcat.context_processors.messages')
    def test_set_maintenance_overlay(self, mock_messsages, mock_cache):
        mock_cache.get = MagicMock(return_value=None)
        with patch('qcat.context_processors.open',
                   mock_open(read_data=self.when), create=True):
            announcement = MaintenanceAnnouncement
            announcement.get_full_maintenance_text = \
                lambda self, next_maintenance_time: sentinel.text
            self.assertDictEqual(
                announcement(self.request).overlay,
                {'maintenance_warn_overlay': sentinel.text}
            )

    def test_set_maintenance_overlay_invalid_session(self):
        request = MagicMock(session={'saw_deploy_warning': 'not-a-datetime'})
        announcement = MaintenanceAnnouncement(request=request)
        this_moment = now()
        announcement.set_maintenance_overlay(next_maintenance_time=this_moment)
        self.assertEquals(
            request.session['saw_deploy_warning'], this_moment.isoformat()
        )

    def test_set_maintenance_overlay_with_session(self):
        saw_deploy_time = (now() + timedelta(seconds=30)).isoformat()
        request = MagicMock(session={'saw_deploy_warning': saw_deploy_time})
        announcement = MaintenanceAnnouncement(request=request)
        announcement.set_maintenance_overlay(next_maintenance_time='')
        self.assertEqual(request.session['saw_deploy_warning'], saw_deploy_time)
        self.assertEqual(announcement.overlay, {})
