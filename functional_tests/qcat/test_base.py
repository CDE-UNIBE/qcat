from rest_framework.reverse import reverse
from selenium.common.exceptions import NoSuchElementException

from functional_tests.base import FunctionalTest


class BaseTemplateTest(FunctionalTest):

    def test_warning_is_displayed(self):
        with self.settings(WARN_HEADER='FOO'):
            self.browser.get(self.live_server_url + reverse('home'))
            # Check if the warning box is displayed
            is_displayed = self.browser.find_element_by_class_name(
                'demo-version'
            ).is_displayed()
            self.assertEqual(is_displayed, True)

    def test_warning_is_hidden(self):
        with self.settings(WARN_HEADER=''):
            self.browser.get(self.live_server_url + reverse('home'))
            # Check if the warning box is not displayed
            with self.assertRaises(NoSuchElementException):
                self.browser.find_element_by_class_name(
                    'demo-version'
                )
