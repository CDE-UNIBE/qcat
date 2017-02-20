from unittest import mock

from django.contrib.auth import get_user_model
from model_mommy import mommy
from qcat.tests import TestCase
from questionnaire.models import Questionnaire, QuestionnaireMembership

from notifications.utils import CreateLog, ContentLog, StatusLog, MemberLog, \
    InformationLog


class CreateLogTest(TestCase):

    def setUp(self):
        self.catalyst = mommy.make(get_user_model())
        self.subscriber = mommy.make(get_user_model())
        self.questionnaire = mommy.make(
            Questionnaire
        )
        mommy.make(
            model=QuestionnaireMembership,
            questionnaire=self.questionnaire,
            user=self.catalyst
        )
        mommy.make(
            model=QuestionnaireMembership,
            questionnaire=self.questionnaire,
            user=self.subscriber
        )

        self.create_log = CreateLog(
            sender=self.catalyst,
            action=123,
            questionnaire=self.questionnaire
        )

    def test_init_questionnaire(self):
        with mock.patch.object(CreateLog, 'create_log') as create:
            create.return_value = mock.MagicMock()
            questionnaire = mock.MagicMock()
            log = CreateLog(1, 2, questionnaire)
            self.assertEqual(log.questionnaire, questionnaire)

    def test_init_create_log_action(self):
        self.assertEqual(self.create_log.log.action, 123)

    def test_init_create_log_catalyst(self):
        self.assertEqual(self.create_log.log.catalyst, self.catalyst)

    def test_init_create_log_questionnaire(self):
        self.assertEqual(self.create_log.log.questionnaire, self.questionnaire)

    def test_init_create_log_subscriber(self):
        self.assertQuerysetEqual(
            self.create_log.log.subscribers.all(), [self.subscriber.id],
            transform=lambda log: log.id
        )


class ContentLogTest(TestCase):

    @mock.patch('notifications.utils.ContentUpdate.objects.create')
    def test_create(self, mock_create):
        instance = mock.MagicMock()
        instance.log = 'log'
        instance.questionnaire.data = 'data'
        ContentLog.create(self=instance)
        mock_create.assert_called_once_with(log='log', data='data')


class StatusLogTest(TestCase):

    @mock.patch('notifications.utils.StatusUpdate.objects.create')
    def test_create(self, mock_create):
        instance = mock.MagicMock()
        instance.log = 'log'
        instance.questionnaire.status = 'status'
        StatusLog.create(self=instance, is_rejected='is_rejected', message='bar')
        mock_create.assert_called_once_with(
            log='log', status='status', is_rejected='is_rejected', message='bar'
        )


class MemberLogTest(TestCase):

    @mock.patch('notifications.utils.MemberUpdate.objects.create')
    def test_create(self, mock_create):
        instance = mock.MagicMock()
        instance.log = 'log'
        MemberLog.create(self=instance, affected='user', role='role')
        mock_create.assert_called_once_with(
            log='log', affected='user', role='role'
        )

class InformationUpdateTest(TestCase):

    @mock.patch('notifications.utils.InformationUpdate.objects.create')
    def test_create(self, mock_create):
        instance = mock.MagicMock()
        instance.log = 'log'
        InformationLog.create(self=instance, info='foo')
        mock_create.assert_called_once_with(
            log='log', info='foo'
        )
