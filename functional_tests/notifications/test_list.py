from unittest.mock import patch, MagicMock

import time
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from model_mommy import mommy
from notifications.models import Log, StatusUpdate, ReadLog
from notifications.views import LogListView, LogQuestionnairesListView
from questionnaire.models import Questionnaire

from functional_tests.base import FunctionalTest


class NotificationSetupMixin:
    """
    Shared setup functionalities
    """

    def setUp(self):
        super().setUp()
        # create some users.
        self.robin = mommy.make(get_user_model(), firstname='robin')
        self.jay = mommy.make(get_user_model(), firstname='jay')

        # and a log that is ready for review.
        questionnaire = mommy.make(
            model=Questionnaire,
            status=settings.QUESTIONNAIRE_SUBMITTED
        )
        self.review_log = mommy.make(
            model=Log,
            questionnaire=questionnaire,
            catalyst=self.jay,
            action=settings.NOTIFICATIONS_CHANGE_STATUS
        )
        mommy.make(
            model=StatusUpdate,
            log=self.review_log,
            status=settings.QUESTIONNAIRE_SUBMITTED
        )

        # helpers
        self.profile_url = '{base}{profile}'.format(
            base=self.live_server_url,
            profile=reverse('account_questionnaires')
        )
        self.notifications_xpath = "//div[(contains(@class, 'notification-list') " \
                                   " and not(contains(@class, 'header')))]"

    def create_status_log(self, user):
        log = mommy.make(
            Log,
            catalyst=user,
            action=settings.NOTIFICATIONS_CHANGE_STATUS
        )
        mommy.make(model=StatusUpdate, log=log)


class ProfileNotificationsTest(NotificationSetupMixin, FunctionalTest):

    def test_notification_display(self):
        # From a logged in state, open the profile page
        self.doLogin(user=self.robin)
        self.browser.get(self.profile_url)
        # no notifications are available
        self.assertTrue(
            'No notifications.' in
            self.findBy('id', 'latest-notification-updates').text
        )
        # create a new notification
        self.create_status_log(self.robin)
        # After a reload, the notification for robin is shown, displaying one
        # notification log.
        self.browser.get(self.profile_url)
        self.browser.implicitly_wait(1)
        logs = self.findManyBy('xpath', self.notifications_xpath)
        self.assertEqual(len(logs), 1)
        # and the pagination is available.
        self.findBy('class_name', 'pagination-centered')


    @patch('django.contrib.auth.backends.ModelBackend.get_all_permissions')
    def test_todo_notification(self, mock_permissions):
        # Robin is now also a reviewer and logs in
        mock_permissions.return_value = ['questionnaire.review_questionnaire']
        self.doLogin(user=self.robin)
        self.browser.get(self.profile_url)

        # Exactly one notification and the label for 'pending' is shown.
        logs = self.findManyBy('xpath', self.notifications_xpath)
        self.assertEqual(len(logs), 1)
        self.findBy('class_name', 'has-unread-messages')

        # There is only one checkbox, so click it.
        checkbox = self.findBy('class_name', 'mark-done')
        checkbox.click()
        # After a little processing, the whole row is now marked as read and a
        # model entry is stored
        time.sleep(1)
        self.assertTrue('is-read' in logs[0].get_attribute('class'))
        self.assertTrue(
            ReadLog.objects.filter(
                user=self.robin, log=self.review_log, is_read=True
            )
        )
        # But the click was a mistake, the notification is not done yet, so
        # the checkbox is clicked again - and all is back to normal.
        checkbox.click()
        self.assertTrue('is-read' not in logs[0].get_attribute('class'))
        self.assertTrue(
            ReadLog.objects.filter(
                user=self.robin, log=self.review_log, is_read=False
            )
        )

    def test_no_todo_notification(self):
        # For the compiler of this log, jay, the is-pending label is not shown.
        self.doLogin(user=self.jay)
        self.browser.get(self.profile_url)
        logs = self.findManyBy('xpath', self.notifications_xpath)
        self.assertEqual(len(logs), 1)
        self.findByNot('xpath', "//svg[(contains(@class, 'alert')]")

    def test_pagination(self):
        for i in range(9):
            self.create_status_log(self.jay)
        # Jay has many notifications, but only a slice is shown.
        self.doLogin(user=self.jay)
        self.browser.get(self.profile_url)
        logs = self.findManyBy('xpath', self.notifications_xpath)
        self.assertEqual(len(logs), settings.NOTIFICATIONS_TEASER_PAGINATE_BY)

        # The other notifications are paginated. The 'previous' button is not
        # available on the first page.
        pagination = self.findBy(
            'id', 'latest-notification-updates'
        ).find_element_by_class_name(
            'pagination'
        )
        pagination_elements = pagination.find_elements_by_tag_name('li')
        self.assertTrue(
            'unavailable' in pagination_elements[0].get_attribute('class')
        )
        # The first page is marked as current page.
        self.assertTrue(
            pagination_elements[1].get_attribute('class') == 'current'
        )
        # When clicking on the next page
        pagination_elements[2].click()
        time.sleep(1)
        pagination = self.findBy(
            'id', 'latest-notification-updates'
        ).find_element_by_class_name(
            'pagination'
        )
        pagination_elements = pagination.find_elements_by_tag_name('li')
        # the second page is 'current'
        self.assertTrue(
            pagination_elements[2].get_attribute('class') == 'current'
        )
        # the 'previous' arrow is available
        self.assertTrue(
            'unavailable' not in pagination_elements[0].get_attribute('class')
        )
        # and new notifications are shown
        self.assertFalse(logs == self.findManyBy('class_name', 'notification-list'))


class NotificationsListTest(NotificationSetupMixin, FunctionalTest):
    """
    As most functionality is tested on the profile view, this contains mainly
    tests for the structure of the dedicated notifications page.
    """

    def setUp(self):
        super().setUp()
        self.relative_notifications_url = reverse('notification_list')
        self.notifications_url = '{base}{notifications_list}'.format(
            base=self.live_server_url,
            notifications_list=self.relative_notifications_url
        )

    def test_follow_profile_link(self):
        # After logging in, jay follows the link to view all notifications
        self.doLogin(user=self.jay)
        self.browser.get(self.profile_url)
        link = self.findBy('xpath', '//a[@href="{}"]'.format(self.relative_notifications_url))
        self.assertEqual(
            link.get_attribute('href'), self.notifications_url
        )

    def test_notifications_list(self):
        # Jay logs in and visits the notifications page
        self.doLogin(user=self.jay)
        self.browser.get(self.notifications_url)

        # A box to select only pending notifications is shown
        self.findBy('id', 'is-pending')

        # The actual list contains one element only
        notifications = self.findBy(
            'id', 'notifications-list'
        ).find_elements_by_xpath(self.notifications_xpath)
        self.assertEqual(1, len(notifications))

    def test_empty_notifications_list(self):
        # Robin logs in and visits the notifications page
        self.doLogin(user=self.robin)
        self.browser.get(self.notifications_url)
        # but no notifications are shown.
        notifications = self.findBy('id', 'notifications-list')
        self.assertTrue('No notifications.' in notifications.text)

    def test_pagination(self):
        # could be made nicer with recipes.
        for i in range(18):
            self.create_status_log(self.jay)

        # Jay has many notifications, but only a slice is shown.
        self.doLogin(user=self.jay)
        self.browser.get(self.notifications_url)
        logs = self.findManyBy('xpath', self.notifications_xpath)
        self.assertEqual(len(logs), settings.NOTIFICATIONS_LIST_PAGINATE_BY)

    @patch('django.contrib.auth.backends.ModelBackend.get_all_permissions')
    def test_todo_notifications(self, mock_permissions):
        log = mommy.make(
            Log,
            catalyst=self.robin,
            action=settings.NOTIFICATIONS_CHANGE_STATUS
        )
        mommy.make(StatusUpdate, log=log)

        # Robin is now also a reviewer and logs in
        mock_permissions.return_value = ['questionnaire.review_questionnaire']
        self.doLogin(user=self.robin)
        self.browser.get(self.notifications_url)
        # Initially, a massive amount of two notifications is shown.
        elements = self.findManyBy('xpath', self.notifications_xpath)
        self.assertEqual(2, len(elements))
        # So Robin clicks the box to filter only 'pending' logs, resulting in
        # one log only.
        self.findBy('id', 'is-pending').click()
        self.assertEqual(
            1, len(self.findManyBy('xpath', self.notifications_xpath))
        )
        # After clicking the box again, all logs are shown.
        self.findBy('id', 'is-pending').click()
        self.assertEqual(
            2, len(self.findManyBy('xpath', self.notifications_xpath))
        )

    @patch.object(LogListView, 'add_user_aware_data')
    @patch('django.contrib.auth.backends.ModelBackend.get_all_permissions')
    def test_todo_notifications_get_param(self, mock_permissions, mock_user_aware_data):
        mock_user_aware_data.return_value = yield MagicMock()
        # Robin the reviewer visits the page for notifications with the
        # get-parameter to show pending logs only.
        mommy.make(Log, catalyst=self.robin, _quantity=3)
        mock_permissions.return_value = ['questionnaire.review_questionnaire']
        self.doLogin(user=self.robin)
        self.browser.get('{}?is_pending'.format(self.notifications_url))
        # Only the one pending log is shown, and the checkbox is active.
        self.assertEqual(
            1, len(self.findManyBy('class_name', 'notification-list'))
        )
        self.assertEqual(
            'true', self.findBy('id', 'is-pending').get_attribute('checked')
        )

        # After clicking on the checkbox, all notifications are shown.
        self.findBy('id', 'is-pending').click()
        time.sleep(1)
        self.assertEqual(
            4, len(self.findManyBy('class_name', 'notification-list'))
        )

    def test_filter_approve(self):
        # Jay logs in
        self.doLogin(user=self.jay)
        self.browser.get(self.notifications_url)
        # And clicks the filter for 'approve'
        self.findBy('id', 'is-pending').click()
        # the filter is now active, and the list empty.
        pending = self.findBy('id', 'is-pending')
        self.assertTrue('is-active-filter' in pending.get_attribute('class'))
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            0
        )
        # A new notification is created by another person
        self.create_status_log(self.jay)
        # jay reloads the page, applies the same filter again, and the element
        # is visible.
        self.browser.get(self.notifications_url)
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            Log.actions.user_log_list(self.jay).count()
        )

        # however, the element is also not pending.
        self.findBy('id', 'is-pending').click()
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            0
        )

    def test_filter_read(self):
        # jay just doesn't get enough of these notifications. so the page is
        # opened.
        self.doLogin(user=self.jay)
        self.browser.get(self.notifications_url)
        # the filter for 'read' is not set yet
        self.assertFalse(
            'is-active-filter' in
            self.findBy('id', 'is-unread').get_attribute('class')
        )
        # jay clicks the filter for 'read' logs
        self.findBy('id', 'is-unread').click()
        # the filter is now unactive, and the list empty.
        self.assertTrue(
            'is-active-filter' in
            self.findBy('id', 'is-unread').get_attribute('class'))
        # one element is shown.
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            1
        )
        # jay has read this element and clicks on the indicator on the page
        # header
        self.findBy('class_name', 'mark-done').click()
        self.findBy('class_name', 'notification-indicator').click()
        # the filter is now switched on by default.
        self.assertTrue(
            'is-active-filter' in
            self.findBy('id', 'is-unread').get_attribute('class')
        )
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            0
        )

    @patch.object(LogQuestionnairesListView, 'get_questionnaire_logs')
    def test_filter_questionnaire(self, mock_get_list):
        mock_get_list.return_value = ['foo_1', 'bar_2']
        # Robin opens the notifications page
        self.doLogin(user=self.robin)
        self.browser.get(self.notifications_url)
        # and clicks on the filter for 'questionnaire', opening the dropdown
        self.findBy('id', 'questionnaire-filter-toggler').click()
        self.findBy('id', 'questionnaire-filter').is_displayed()
        self.findBy('class_name', 'chosen-container').click()
        select = self.findBy('class_name', 'chosen-results').find_elements_by_tag_name('li')
        # there are three options available ('all' and the mock return_values)
        self.assertEqual(
            len(select),
            3
        )
        # robin clicks the second element and the filter is now active
        select[2].click()
        # self.wait_for doesn't work, as the elemnt is in the dom already.
        time.sleep(1)
        self.assertTrue(
            'is-active-filter' in
            self.findBy('id', 'questionnaire-filter-toggler').get_attribute('class')
        )

    def test_filter_status(self):
        # jay logs in and visits the notifications page; one item is shown
        self.doLogin(user=self.jay)
        self.browser.get(self.notifications_url)
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            1
        )
        # after clicking the filter item for the status, the dropdown opens
        self.findBy('class_name', 'is-status-dropdown').click()
        dropdown = self.findBy('id', 'status-dropdown')
        self.assertTrue(dropdown.is_displayed())
        # jay clicks on the third element, and then the submit button
        self.findBy('id', 'checkbox-3').click()
        self.findBy('id', 'status-filter-submit').click()
        # the container reloads, and the list is now empty
        time.sleep(1)
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            0
        )

    def test_mark_all_read(self):
        # robin logs in and visits the notifications-page
        self.create_status_log(user=self.robin)
        self.doLogin(user=self.robin)
        self.browser.get(self.notifications_url)
        # one unread message is shown, and no unread message
        unmuted = self.notifications_xpath + '/div[@class="is-muted"]'
        self.assertEqual(
            len(self.findManyBy('xpath', self.notifications_xpath)),
            1
        )
        self.assertEqual(
            len(self.findManyBy('xpath', unmuted)),
            0
        )
        # the settings-button is displayed, but the options are hidden
        toggler = self.findBy('xpath', '//button[@data-toggle="notification-settings"]')
        self.assertFalse(
            self.findBy('id', 'notification-settings').is_displayed()
        )
        # after clicking the toggler, the 'read all marked' is visible
        toggler.click()
        time.sleep(1)
        mark_all_read = self.findBy('xpath', '//a[@data-reveal-id="confirm-mark-all-read"]')
        # the overlay is shown
        mark_all_read.click()
        self.wait_for('id', 'confirm-mark-all-read')
        self.assertTrue(
            self.findBy('id', 'confirm-mark-all-read').is_displayed()
        )
        # after clicking on the confirmation button, all messages are read.
        self.findBy('class_name', 'mark-all-read').click()
        self.assertEqual(
            len(self.findManyBy('xpath', unmuted)),
            0
        )
