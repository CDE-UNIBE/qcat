from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from model_mommy import mommy
from selenium.webdriver.support.select import Select

from functional_tests.base import FunctionalTest
from notifications.models import MailPreferences


class MailPreferencesTest(FunctionalTest):

    def setUp(self):
        super().setUp()
        self.user = mommy.make(get_user_model(), firstname='jay')
        self.obj = self.user.mailpreferences

    def test_signed_preferences(self):
        # jay opens the link with the signed url stated in the mail.
        signed_url = self.live_server_url + str(self.obj.get_signed_url())
        self.browser.get(signed_url)
        # no spam please - change the value in the subscription box
        select = Select(self.findBy('id', 'id_subscription'))
        select.select_by_value('none')
        # the actions are disabled now.
        action = self.findBy('id', 'id_wanted_actions_2')
        self.assertTrue(
            action.get_attribute('disabled')
        )
        # submit the form
        self.findBy('xpath', '//input[@type="submit"]').click()
        # the success message is shown
        self.wait_for('class_name', 'notification')
        self.assertEqual(
            self.browser.current_url, signed_url
        )
        select = Select(self.findBy('id', 'id_subscription'))
        self.assertEqual(
            select.first_selected_option.get_attribute('value'),
            settings.NOTIFICATIONS_NO_MAILS
        )

    def test_user_preferences(self):
        unsigned_url = self.live_server_url + reverse('notification_preferences')
        self.browser.get(unsigned_url)
        # ah, a login is required
        self.assertEqual(
            self.findBy('class_name', 'is-title').text, 'Login'
        )
        self.doLogin(user=self.user)
        # after the login, the preferences are shown
        self.browser.get(unsigned_url)
        # without changing anything, the form is submitted
        self.findBy('xpath', '//input[@type="submit"]').click()
        # and still, the url without signed id is used.
        self.assertEqual(
            self.browser.current_url,
            unsigned_url
        )
        # jay now changes the language and saves again.
        select = Select(self.findBy('id', 'id_language'))
        select.select_by_value('es')
        self.findBy('xpath', '//input[@type="submit"]').click()
        # after the success message is shown, the flag is set that the language
        # is not overridden anymore.
        self.wait_for('class_name', 'notification')
        self.assertTrue(
            MailPreferences.objects.get(user__firstname='jay').has_changed_language
        )
