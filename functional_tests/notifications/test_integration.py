from unittest.mock import patch

import time
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from model_mommy import mommy

from accounts.middleware import WocatAuthenticationMiddleware
from configuration.models import Configuration
from questionnaire.models import Questionnaire, QuestionnaireMembership, \
    QuestionnaireConfiguration

from functional_tests.base import FunctionalTest


@patch.object(WocatAuthenticationMiddleware, 'process_request')
class NotificationsIntegrationTest(FunctionalTest):
    """
    Specific tests for triggering and displaying of notifications

    jay is a compiler
    robin is an editor
    """
    fixtures = ['sample_global_key_values', 'sample']

    def setUp(self):
        super().setUp()
        self.jay = mommy.make(
            get_user_model(),
            firstname='jay'
        )
        self.robin = mommy.make(
            get_user_model(),
            firstname='robin'
        )
        self.questionnaire = mommy.make(
            model=Questionnaire,
            data={},
            code='sample_1',
            status=settings.QUESTIONNAIRE_DRAFT,
        )
        # Create a valid questionnaire with the least required data.
        mommy.make(
            model=QuestionnaireConfiguration,
            questionnaire=self.questionnaire,
            configuration=Configuration.objects.filter(code='sample').first(),
            original_configuration=True
        )
        mommy.make(
            model=QuestionnaireMembership,
            user=self.jay,
            questionnaire=self.questionnaire,
            role='compiler'
        )
        mommy.make(
            model=QuestionnaireMembership,
            user=self.robin,
            questionnaire=self.questionnaire,
            role='editor'
        )
        self.notifications_url = '{}{}'.format(
            self.live_server_url,
            reverse('notification_list')
        )
        self.questionnaire_edit_url = '{}{}'.format(
            self.live_server_url,
            self.questionnaire.get_edit_url()
        )

    def test_compiler_edit_questionnaire(self, mock_process_request):
        mock_process_request.return_value = None
        # The compiler logs in and doesn't see the button to finish editing.
        self.doLogin(user=self.jay)
        self.browser.get(self.questionnaire_edit_url)
        self.findBy('id', 'confirm-submit')
        self.findByNot('class_name', 'is-finished-editing')

    def test_create_message(self, mock_process_request):
        """
        Note: I'm not sure if time.sleep is correct here, but self.wait_until
        seems to defeat the purpose.
        """
        mock_process_request.return_value = None
        # the editor logs in and sees the button to finish editing.
        self.doLogin(user=self.robin)
        self.browser.get(self.questionnaire_edit_url)
        finish_editing = self.findBy('class_name', 'is-finished-editing')
        finish_editing.click()
        # the message box pops up and robin fills in a message for the compiler
        self.wait_for('id', 'finish-editing')
        self.assertTrue(
            self.findBy('id', 'finish-editing').is_displayed()
        )
        self.findBy('name', 'compiler_info_message').send_keys('i am done')
        # finally, robin clicks the button to submit the message.
        self.findBy('id', 'inform-compiler').click()
        # as robin checks new notifications, the notification is not on display
        self.browser.get(self.notifications_url)
        boxes = self.findBy(
            'id', 'notifications-list'
        ).find_elements_by_tag_name('div')
        self.assertEqual(
            boxes[7].text,
            'No notifications.'
        )

        # some time later, jay the compiler logs in and visits the notifications
        # page.
        self.doLogin(self.jay)
        # the indicator for new messages is shown, so jay visits the
        # notifications page
        time.sleep(0.5)
        self.findBy('class_name', 'has-unread-messages')
        self.browser.get(self.notifications_url)
        # the notification from robin is shown.
        boxes = self.findBy(
            'id', 'notifications-list'
        ).find_elements_by_tag_name('div')
        self.assertTrue(
            'sample_1 editing has been finalized by robin' in boxes[7].text
        )
        # jay clicks on the mail icon and the message is revealed in full.
        self.findBy('xpath', '//a[@data-reveal-id="show-message-1"]').click()
        time.sleep(0.5)
        modal = self.findBy('id', 'show-message-1')
        self.assertTrue(
            modal.is_displayed()
        )
        self.assertEqual(
            modal.find_element_by_tag_name('p').text,
            'i am done'
        )


