# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from unittest.mock import patch, MagicMock

from qcat.tests import TestCase
from questionnaire.signals import create_questionnaire, delete_questionnaire, \
    change_status, change_member, change_questionnaire_data


class ReceiverTest(TestCase):
    """
    Test only proper method calls. Functionality of the statuslog etc. is tested
    in test_utils.py
    """

    def setUp(self):
        super().setUp()
        self.questionnaire = MagicMock(status=3)

    def _test_init_call(self, signal, log_type, **kwargs):
        with patch('notifications.receivers.{}'.format(log_type)) as mock_status_log:
            getattr(signal, 'send')(
                sender='sender',
                questionnaire=self.questionnaire,
                user='user',
                **kwargs
            )
            mock_status_log.assert_called_once_with(
                action='sender', sender='user',
                questionnaire=self.questionnaire,
                signal=signal,
            )

    def _test_create_call(self, signal, log_type, do_assert_call=True, **kwargs):
        questionnaire = kwargs.pop('questionnaire', self.questionnaire)

        with patch('notifications.receivers.{}.create_log'.format(log_type)) as init:
            init.return_value = MagicMock()
            with patch('notifications.receivers.{}.create'.format(log_type)) as create:
                getattr(signal, 'send')(
                    sender='sender',
                    questionnaire=questionnaire,
                    user='user',
                    **kwargs
                )
                if do_assert_call:
                    create.assert_called_once_with(**kwargs)
                else:
                    return create

    # Testing all these calls could be done in a loop - this is more explicit.
    def test_create_questionnaire(self):
        self._test_init_call(signal=create_questionnaire, log_type='StatusLog')

    def test_create_questionnaire_create(self):
        self._test_create_call(
            signal=create_questionnaire, log_type='StatusLog',
            is_rejected=False, message=_('Created')
        )

    def test_delete_questionnaire(self):
        self._test_init_call(signal=delete_questionnaire, log_type='StatusLog')

    def test_delete_questionnaire_create(self):
        self._test_create_call(
            signal=delete_questionnaire, log_type='StatusLog',
            is_rejected=False, message=_('Deleted')
        )

    def test_change_status(self):
        self._test_init_call(signal=change_status, log_type='StatusLog')

    def test_change_status_create(self):
        self._test_create_call(
            signal=change_status, log_type='StatusLog',
            is_rejected=False, message=''
        )

    def test_change_member(self):
        self._test_init_call(
            signal=change_member, log_type='MemberLog',
            affected='user', role='foo'
        )

    def test_change_member_create(self):
        create_call = self._test_create_call(
            signal=change_member, log_type='MemberLog',
            do_assert_call=False,
            is_rejected=False, message='',
            affected='user', role='foo'
        )
        create_call.assert_called_once_with(affected='user', role='foo')

    def test_change_questionnaire_data(self):
        self._test_init_call(
            signal=change_questionnaire_data, log_type='ContentLog'
        )

    def test_change_questionnaire_data_create(self):
        create_call = self._test_create_call(
            signal=change_questionnaire_data, log_type='ContentLog',
            do_assert_call=False,
        )
        create_call.assert_called_once_with()
