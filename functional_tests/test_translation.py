from unittest.mock import patch

from django.core.urlresolvers import reverse

from functional_tests.base import FunctionalTest


class TranslationTest(FunctionalTest):

    @patch('wocat.views.generic_questionnaire_list')
    def test_change_languages(self, mock_list):
        mock_list.return_value = {}

        # Alice opens her web browser and goes to the home page.
        self.browser.get('{}{}'.format(
            self.live_server_url, reverse('home')
        ))

        # She sees that the page is in English because the available languages
        # are written in English.
        self.checkOnPage('English')
        self.checkOnPage('Español')

        # She changes the language to Spanish and sees that the available
        # languages are now written in Spanish.
        self.changeLanguage('es')
        self.checkOnPage('English')
        self.checkOnPage('Español')
