from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.conf import settings
from django.test import override_settings
from model_mommy import mommy
from qcat.tests import TestCase

from notifications.models import ActionContextQuerySet, Log, StatusUpdate, \
    ReadLog, ContentUpdate
from questionnaire.models import Questionnaire, QuestionnaireMembership


class ActionContextTest(TestCase):

    def make_user(*permissions, **attributes):
        """
        Helper for user creation, as the method 'get_all_permissions' is crucial,
        but creating groups and permissions is too much overhead.
        """
        user = mommy.make(
            model=get_user_model(),
            **attributes,
        )
        user.get_all_permissions = lambda: permissions
        return user

    def setUp(self):
        self.qs = ActionContextQuerySet()

        change_permissions = 'questionnaire.change_questionnaire'
        review_permissions = 'questionnaire.review_questionnaire'
        publish_permissions = 'questionnaire.publish_questionnaire'

        # Users with all relevant roles
        self.admin = self.make_user(change_permissions, review_permissions, publish_permissions)
        self.catalyst = self.make_user()
        self.subscriber = self.make_user()
        self.reviewer = self.make_user(change_permissions)
        self.reviewer = self.make_user(review_permissions)
        self.publisher = self.make_user(publish_permissions)

        self.questionnaire = mommy.make(
            Questionnaire,
            status=settings.QUESTIONNAIRE_SUBMITTED
        )

        # Notification for a submitted questionnaire
        self.catalyst_change = mommy.make(
            model=Log,
            action=settings.NOTIFICATIONS_CHANGE_STATUS,
            catalyst=self.catalyst,
            questionnaire=self.questionnaire
        )
        self.catalyst_change.subscribers.add(self.subscriber)
        mommy.make(
            StatusUpdate,
            log=self.catalyst_change,
            status=settings.QUESTIONNAIRE_SUBMITTED
        )

        # Notification the should not be listed
        self.catalyst_edit = mommy.make(
            model=Log,
            action=settings.NOTIFICATIONS_EDIT_CONTENT,
            catalyst=self.catalyst,
            questionnaire=self.questionnaire
        )

        self.admin_read_log = mommy.make(
            ReadLog,
            user=self.admin,
            log=self.catalyst_change,
            is_read=True
        )

    # assertQuerysetEqual uses the models 'repr' method to check its 'sameness'.
    # However, this seems not stable, so we use the models id.
    transform = lambda self, x: x.id

    @override_settings(NOTIFICATIONS_CHANGE_STATUS='baz')
    @override_settings(NOTIFICATIONS_QUESTIONNAIRE_STATUS_PERMISSIONS={'foo': 'bar'})
    @patch.object(QuestionnaireMembership, 'objects')
    def test_get_questionnaires_for_permissions(self, mock_membership):
        mock_membership.return_value = []
        user = MagicMock(get_all_permissions=lambda: ['foo'])
        permissions = self.qs.get_questionnaires_for_permissions(user=user)
        # asserting strings is a workaround. tried assertListEqual and
        # assertQuerysetEqual, but they raise errors for unknown reasons.
        self.assertEqual(
            permissions[0].__str__(),
            Q(statusupdate__status='bar', action='baz').__str__()
        )

    @override_settings(NOTIFICATIONS_QUESTIONNAIRE_STATUS_PERMISSIONS={'foo': 'bar'})
    @patch.object(QuestionnaireMembership, 'objects')
    def test_get_questionnaires_without_permissions(self, mock_membership):
        user = MagicMock(get_all_permissions=lambda: ['bar'])
        mock_membership.return_value = []
        permissions = self.qs.get_questionnaires_for_permissions(user=user)
        self.assertEqual(permissions, [])

    def test_permissions_questionnaire_membership(self):
        user = mommy.make(get_user_model())
        mommy.make(
            model=QuestionnaireMembership,
            questionnaire=self.questionnaire,
            user=user,
            role=settings.QUESTIONNAIRE_REVIEWER
        )
        self.assertEqual(
            Log.actions.user_pending_list(user).count(),
            1
        )

    def test_user_log_list_catalyst(self):
        self.assertQuerysetEqual(
            Log.actions.user_log_list(self.catalyst),
            [self.catalyst_change.id],
            transform=self.transform
        )

    def test_user_log_list_subscriber(self):
        self.assertQuerysetEqual(
            Log.actions.user_log_list(self.subscriber),
            [self.catalyst_change.id],
            transform=self.transform
        )

    def test_user_log_list_admin_permissions(self):
        self.assertQuerysetEqual(
            Log.actions.user_log_list(self.admin),
            [self.catalyst_change.id],
            transform=self.transform
        )

    def test_user_log_list_reviewer_permissions(self):
        self.assertQuerysetEqual(
            Log.actions.user_log_list(self.reviewer),
            [self.catalyst_change.id],
            transform=self.transform
        )

    def test_user_log_list_publisher_permissions(self):
        self.assertFalse(
            Log.actions.user_log_list(self.publisher).exists()
        )

    def test_list_includes_edit_for_compiler(self):
        mommy.make(
            model=QuestionnaireMembership,
            questionnaire=self.questionnaire,
            user=self.catalyst,
            role=settings.QUESTIONNAIRE_COMPILER
        )
        self.assertTrue(
            self.catalyst_edit in Log.actions.user_log_list(self.catalyst)
        )

    def test_user_pending_list_reviewer_has_log(self):
        self.assertQuerysetEqual(
            Log.actions.user_pending_list(self.reviewer),
            [self.catalyst_change.id],
            transform=self.transform
        )

    def test_user_pending_list_admin_has_no_logs(self):
        # admin has read the notification
        self.assertFalse(
            Log.actions.user_pending_list(self.admin).exists()
        )

    def test_user_pending_list_publisher_has_no_logs(self):
        self.assertFalse(
            Log.actions.user_pending_list(self.publisher).exists()
        )

    def test_user_log_count(self):
        # Test count for all unread questionnaires
        catalyst_change_old = mommy.make(
            model=Log,
            action=settings.NOTIFICATIONS_CHANGE_STATUS,
            catalyst=self.catalyst,
            questionnaire=self.questionnaire
        )
        mommy.make(
            StatusUpdate,
            log=catalyst_change_old,
            status=settings.QUESTIONNAIRE_SUBMITTED
        )

        self.assertQuerysetEqual(
            Log.actions.user_log_list(self.reviewer),
            [catalyst_change_old.id, self.catalyst_change.id],
            transform=self.transform
        )

        self.assertEqual(
            Log.actions.user_log_count(self.reviewer),
            2
        )

    def test_only_unread_logs(self):
        self.assertQuerysetEqual(
            Log.actions.only_unread_logs(self.catalyst),
            [self.catalyst_edit.id, self.catalyst_change.id],
            transform=self.transform
        )

    def test_only_unread_logs_is_read(self):
        mommy.make(
            model=ReadLog,
            is_read=True,
            user=self.catalyst,
            log=self.catalyst_edit
        )
        self.assertQuerysetEqual(
            Log.actions.only_unread_logs(self.catalyst),
            [self.catalyst_change.id],
            transform=self.transform
        )

    def test_only_unread_logs_is_not_read(self):
        mommy.make(
            model=ReadLog,
            is_read=False,
            user=self.catalyst,
            log=self.catalyst_edit
        )
        self.assertQuerysetEqual(
            Log.actions.only_unread_logs(self.catalyst),
            [self.catalyst_edit.id, self.catalyst_change.id],
            transform=self.transform
        )

    def test_user_log_roles(self):
        # subscriber and catalyst should see the log 'catalyst_change'
        roles = {'subscriber': 1, 'catalyst': 1, 'publisher': 0}
        for role, logs in roles.items():
            self.assertEqual(
                Log.actions.user_log_count(getattr(self, role)), logs
            )

    def test_read_logs_admin(self):
        self.assertQuerysetEqual(
            Log.actions.read_logs(user=self.admin),
            [self.admin_read_log.id],
            transform=self.transform
        )

    def test_read_logs_subscriber(self):
        self.assertFalse(
            Log.actions.read_logs(self.catalyst).exists()
        )

    def test_read_id_list(self):
        self.assertListEqual(
            list(Log.actions.read_id_list(self.admin)),
            [self.catalyst_change.id]
        )

    @patch.object(ActionContextQuerySet, 'delete_all_read_logs')
    def test_mark_all_read_deletes_all(self, mock_delete):
        Log.actions.mark_all_read(user=self.subscriber)
        mock_delete.assert_called_once()

    def test_mark_all_read(self):
        Log.actions.mark_all_read(user=self.catalyst)
        self.assertTrue(
            ReadLog.objects.filter(user=self.catalyst, is_read=True).exists()
        )

    def test_delete_all_read_logs(self):
        mommy.make(ReadLog, user=self.subscriber)
        Log.actions.delete_all_read_logs(user=self.subscriber)
        self.assertFalse(
            ReadLog.objects.filter(user=self.subscriber)
        )


class LogTest(TestCase):

    def setUp(self):
        self.catalyst = mommy.make(
            model=get_user_model()
        )
        self.status_log = mommy.make(
            model=Log,
            action=settings.NOTIFICATIONS_CHANGE_STATUS,
            catalyst=self.catalyst
        )
        mommy.make(
            model=StatusUpdate,
            log=self.status_log
        )
        self.content_log = mommy.make(
            model=Log,
            action=settings.NOTIFICATIONS_EDIT_CONTENT
        )
        mommy.make(
            model=ContentUpdate,
            log=self.content_log
        )

    def test_is_content_update(self):
        self.assertTrue(self.content_log.is_content_update)

    def test_is_not_content_update(self):
        self.assertFalse(self.status_log.is_content_update)

    @patch('notifications.models.render_to_string')
    def test_get_linked_subject(self, render_to_string):
        self.status_log.get_linked_subject(self.catalyst)
        render_to_string.assert_called_with(
            template_name='notifications/subject/{}.html'.format(
                settings.NOTIFICATIONS_CHANGE_STATUS
            ),
            context={'log': self.status_log, 'user': self.catalyst}
        )
