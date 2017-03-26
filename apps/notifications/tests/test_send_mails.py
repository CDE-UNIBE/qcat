import contextlib

import collections
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.core.mail.backends.locmem import EmailBackend
from django.core.management import call_command
from django.test import override_settings

from model_mommy import mommy
from unittest.mock import patch

from configuration.models import Configuration
from notifications.models import MailPreferences, Log
from notifications.utils import StatusLog, MemberLog
from qcat.tests import TestCase
from questionnaire.models import Questionnaire, QuestionnaireMembership


class SendMailRecipientMixin(TestCase):
    """
    Helpers to create logs, mock sending with django email backend, and check
    sent mails.
    """

    fixtures = ['groups_permissions', 'sample']
    # map user names to their permission-groups.
    user_groups_mapping = {
        'editor': None,
        'compiler': None,
        'reviewer': 3,
        'publisher': 4,
        'secretariat': 5
    }

    def setUp(self):
        self.create_users()

        self.questionnaire = mommy.make(
            Questionnaire, status=settings.QUESTIONNAIRE_DRAFT,
            configurations=[Configuration.objects.get(code='sample')]
        )

        self.editors = [self.editor_none, self.editor_todo, self.editor_all]
        self.compilers = [self.compiler_none, self.compiler_todo, self.compiler_all]
        self.reviewers = [self.reviewer_none, self.reviewer_todo, self.reviewer_all]
        self.publishers = [self.publisher_none, self.publisher_todo, self.publisher_all]
        self.secretariats = [self.secretariat_none, self.secretariat_todo, self.secretariat_all]
        self.all = [self.editors + self.compilers + self.reviewers + self.publishers + self.secretariats]

    def create_users(self):
        for preference in dict(settings.NOTIFICATIONS_EMAIL_SUBSCRIPTIONS).keys():
            for user, group_id in self.user_groups_mapping.items():
                username = '{user}_{preference}'.format(user=user, preference=preference)
                user_kwargs = {'firstname': username}
                if group_id:
                    user_kwargs['groups'] = [Group.objects.get(id=group_id)]
                self._create_user(username, preference, **user_kwargs)

    def _create_user(self, username, preference, **user_kwargs):
        setattr(self, username, mommy.make(get_user_model(), **user_kwargs))
        mail_preferences = MailPreferences.objects.get(user__firstname=username)
        mail_preferences.subscription = preference
        mail_preferences.save()

    def add_questionnairememberships(self, role: str, *users):
        for user in users:
            mommy.make(
                model=QuestionnaireMembership,
                role=role, user=user, questionnaire=self.questionnaire
            )

    def assert_no_unsent_logs(self, all_logs_count: int):
        """
        Ensure the expected number of logs were created, and all have been sent.
        """
        logs = Log.objects.all()
        self.assertEqual(logs.count(), all_logs_count)
        self.assertFalse(logs.filter(was_sent=False).exists())

    def assert_only_expected(self, outbox, *expected):
        for mail in expected:
            self.assertTrue(
                expr=mail in outbox,
                msg='Expected mail: {} not found in the outbox {}'.format(mail, outbox)
            )

    def filter_expected_logs(self, user: User, logs: list):
        for log in logs:
            if user in log.recipients:
                yield {
                    'log_id': str(log.id),
                    'recipient': user.email,
                    'subject': str(log.mail_subject)
                }

    @contextlib.contextmanager
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def send_notification_mails(self):
        """
        Provide access to all sent messages. Provided attributes should match
        the ones tested for in assert_only_expected.
        """
        outbox = []
        with patch.object(EmailBackend, 'send_messages') as mock_send:
            call_command('send_notification_mails')
            for call in mock_send.call_args_list:
                email_obj = call[0][0][0]
                message = email_obj.message()
                outbox.append({
                    'recipient': email_obj.recipients()[0],
                    'subject': message['Subject'],
                    'log_id': message['qcat_log']
                })

            yield outbox


class PublicationWorkflowMailTest(SendMailRecipientMixin):
    """
    Tests for the typical publication workflow of a questionnaire.
    """
    message_frame = collections.namedtuple("message_frame", "mock_send logs")

    def get_status_log(self, action: int, sender: settings.AUTH_USER_MODEL) -> list:
        status_log = StatusLog(
            action=action, sender=sender, questionnaire=self.questionnaire
        )
        status_log.create(is_rejected=False, message='created')
        return [status_log.log]

    def get_member_log(self, action: int, sender: User, affected: list, role: str) -> list:
        member_logs = []
        for user in affected:
            member_log = MemberLog(
                action=action, sender=sender, questionnaire=self.questionnaire
            )
            member_log.create(affected=user, role=role)
            member_logs.append(member_log.log)
        return member_logs

    def create_logs(self, method_name: str, **kwargs) -> list:
        logs = []
        for user in kwargs.pop('catalysts'):
            logs.extend(getattr(self, method_name)(sender=user, **kwargs))
        return logs

    def test_questionnaire_created(self):
        self.create_logs(
            action=settings.NOTIFICATIONS_CREATE, method_name='get_status_log',
            catalysts=self.compilers
        )
        with self.send_notification_mails() as outbox:
            self.assertEqual(outbox, [])
        self.assert_no_unsent_logs(all_logs_count=3)

    def test_editor_added(self):
        logs = self.create_logs(
            action=settings.NOTIFICATIONS_ADD_MEMBER,
            method_name='get_member_log',
            catalysts=self.compilers,
            affected=self.editors,
            role='editor'
        )
        with self.send_notification_mails() as outbox:
            self.assertEqual(len(outbox), 3)
            expected = self.filter_expected_logs(self.editor_all, logs)
            self.assert_only_expected(outbox, *expected)
        self.assert_no_unsent_logs(all_logs_count=9)

    def test_editor_edited(self):
        pass

    def test_editor_finished(self):
        pass

    def test_questionnaire_submitted(self):
        pass

    def test_questionnaire_review_rejected(self):
        pass

    def test_questionnaire_review_accepted(self):
        pass

    def test_questionnaire_publication_rejected(self):
        pass

    def test_questionnaire_publication_accepted(self):
        pass

    def test_questionnaire_new_version(self):
        pass


# class QuestionnaireCreatedMailTest(SendMailRecipientMixin):
#     """
#     Create logs with various combinations and make sure only the expected
#     recipients are addressed in 'compile_message_to'. Questionnairememberships
#     are copied between versions, so a created questionnaire can have editors
#     and publishers.
#
#     """
#
#     def create_status_logs(self, action, sender):
#         """
#         - catalyst
#         - subscribers
#         - users from permissions
#         - 'affected'
#         - questionnaire memberships
#         """
#         StatusLog(
#             action=action, sender=sender, questionnaire=self.questionnaire
#         ).create(
#             is_rejected=False, message='created'
#         )
#
#     def test_questionnaire_created(self, mock_compile):
#         for compiler in self.compilers:
#             self.create_status_logs(
#                 sender=compiler, action=settings.NOTIFICATIONS_CREATE,
#             )
#         call_command('send_notification_mails')
#         self.assertFalse(mock_compile.called)
#         self.assert_no_unsent_logs()
#
#     def test_questionnaire_created_with_editors(self, mock_compile):
#         for compiler in self.compilers:
#             self.create_status_logs(
#                 sender=compiler, action=settings.NOTIFICATIONS_CREATE,
#             )
#         self.add_questionnairememberships('editor', *self.editors)
#         call_command('send_notification_mails')
#         self.assertFalse(mock_compile.called)
#         self.assert_no_unsent_logs()
#
#     def test_questionnaire_deleted(self, mock_compile):
#         for compiler in self.compilers:
#             self.create_status_logs(
#                 sender=compiler, action=settings.NOTIFICATIONS_DELETE
#             )
#         call_command('send_notification_mails')
#         self.assertFalse(mock_compile.called)
#         self.assert_no_unsent_logs()
#
#     def test_questionnaire_deleted_with_editors(self, mock_compile):
#         for compiler in self.compilers:
#             self.create_status_logs(
#                 sender=compiler, action=settings.NOTIFICATIONS_DELETE
#             )
#         self.add_questionnairememberships('editor', *self.editors)
#         call_command('send_notification_mails')
#         self.assertFalse(mock_compile.called)
#         self.assert_no_unsent_logs()
#
#     def test_questionnaire_edited(self, mock_compile):
#         for editor in self.editors:
#             self.create_status_logs(
#                 sender=editor, action=settings.NOTIFICATIONS_EDIT_CONTENT
#             )
#
#         call_command('send_notification_mails')
#         self.assertFalse(mock_compile.called)
#         self.assert_no_unsent_logs()
#
#     def test_questionnaire_finished_editing(self, mock_compile):
#         for editor in self.editors:
#             self.create_status_logs(
#                 sender=editor, action=settings.NOTIFICATIONS_FINISH_EDITING,
#             )
#         call_command('send_notification_mails')
#         self.assertFalse(mock_compile.called)
#         self.assert_no_unsent_logs()
#
#     # def test_questionnaire_changed_status(self):
#     #     self.create_status_logs(
#     #         settings.NOTIFICATIONS_CHANGE_STATUS,
#     #         self.all
#     #     )
#
#     def test_invited_member(self):
#         pass
#
#     def test_removed_member(self):
#         pass
#
#     def test_edited_questionnaire(self):
#         pass
#
#     def test_finished_editing(self):
#         pass
#
#     def test_wanted_actions(self):
#         pass
