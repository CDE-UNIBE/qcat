import os
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings
from rest_framework.reverse import reverse

from accounts.tests.test_commands import create_new_user
from functional_tests.base import FunctionalTest


@patch('questionnaire.views.generic_questionnaire_list')
class BaseTemplateTest(FunctionalTest):

    def setUp(self):
        super().setUp()
        self.remove_maintenance_file()

    def tearDown(self):
        super().tearDown()
        self.remove_maintenance_file()

    def test_warning_is_displayed(self, mock_questionnaire_list):
        mock_questionnaire_list.return_value = {}
        with self.settings(WARN_HEADER='FOO'):
            self.browser.get(self.live_server_url + reverse('about'))
            # Check if the warning box is displayed
            self.assertTrue(self.browser.find_element_by_xpath(
                '//div[contains(@class, "demo-version")]/*[contains(text(), '
                '"FOO")]'
            ).is_displayed())

    def test_warning_is_hidden(self, mock_questionnaire_list):
        mock_questionnaire_list.return_value = {}
        with self.settings(WARN_HEADER=''):
            self.browser.get(self.live_server_url + reverse('home'))
            # Check if the warning box is not displayed
            self.assertFalse(
                self.browser.find_element_by_class_name(
                    'demo-version'
                ).is_displayed()
            )

    @override_settings(
        DEPLOY_TIMEOUT=600,
        NEXT_MAINTENANCE='envs/TEST_NEXT_MAINTENANCE',
        CACHES={'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
        }
    )
    def test_maintenance_overlay_is_displayed(self, mock_questionnaire_list):
        # Jay logs in and sees no warning.
        jay = create_new_user()
        self.doLogin(jay)
        self.findByNot('id', 'deploy-modal')

        # A deploy is announced, and after the page is reloaded, the overlay is
        # shown
        call_command('set_next_maintenance')
        self.browser.refresh()

        self.wait_for('id', 'deploy-modal')
        modal = self.findBy('id', 'deploy-modal')
        self.assertTrue(modal.text.startswith('Maintenance announcement'))
        # a flash-message is shown too.
        alert_box = self.findBy(
            'xpath', '//div[contains(@class, "notification") and '
                     'contains(@class, "alert-box")]'
        )
        # alert_box.text is empty when the element is hidden
        self.assertTrue(
            alert_box.get_attribute('textContent').startswith('Maintenance '
                                                              'starts in')
        )

        # on the next page, only the flash-message is shown.
        self.browser.refresh()
        self.findByNot('id', 'deploy-modal')
        self.findBy(
            'xpath', '//div[contains(@class, "notification") and '
                     'contains(@class, "alert-box")]'
        )

        # After a logout, the message is not shown anymore.
        self.doLogout()
        self.browser.get(self.live_server_url)
        self.findByNot(
            'xpath', '//div[contains(@class, "notification") and '
                     'contains(@class, "alert-box")]'
        )

        # When logging in again, the deploy is over - no message is shown.
        os.remove('envs/TEST_NEXT_MAINTENANCE')
        self.doLogin(jay)
        self.findByNot(
            'xpath', '//div[contains(@class, "notification") and '
                     'contains(@class, "alert-box")]'
        )

        # After the next page load, the next deploy is announced.
        call_command('set_next_maintenance')
        self.browser.refresh()
        self.wait_for('id', 'deploy-modal')
        self.findBy('id', 'deploy-modal')

    @staticmethod
    def remove_maintenance_file():
        if os.path.isfile('envs/TEST_NEXT_MAINTENANCE'):
            os.remove('envs/TEST_NEXT_MAINTENANCE')

    def test_factsheet(self, mock_questionnaire_list):
        # jay opens the start page
        self.browser.get(self.live_server_url)

        # the home-keynumbers-list is shown after a while, and shows 6
        # entries.
        self.wait_for('class_name', 'home-keynumbers-list')
        keynumbers_list = self.findBy('class_name', 'home-keynumbers-list')
        self.assertEqual(
            len(keynumbers_list.find_elements_by_tag_name('li')),
            6
        )
