from unittest.mock import patch

from django.core.urlresolvers import reverse
from functional_tests.base import FunctionalTest

from wocat.tests.test_views import (
    route_home,
)


class TranslationTest(FunctionalTest):

    @patch('wocat.views.generic_questionnaire_list')
    def test_change_languages(self, mock_list):
        mock_list.return_value = {}

        # Alice goes to the UNCCD app
        self.browser.get(self.live_server_url + reverse(
            route_home))

        # She sees that the page is in English because the available languages
        # are written in English.
        self.checkOnPage('English')
        self.checkOnPage('Español')

        url = self.browser.current_url

        # She changes the language to Spanish and sees that the available
        # languages are now written in Spanish.
        self.changeLanguage('es')
        self.checkOnPage('English')
        self.checkOnPage('Español')

        # She sees that she is still on the same page as before
        self.assertEqual(url.replace('/en/', '/es/'), self.browser.current_url)
