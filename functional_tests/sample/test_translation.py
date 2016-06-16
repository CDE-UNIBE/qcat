from django.core.urlresolvers import reverse
from unittest.mock import patch

from accounts.client import Typo3Client
from functional_tests.base import FunctionalTest
from sample.tests.test_views import (
    route_questionnaire_new,
)


@patch.object(Typo3Client, 'get_user_id')
class TranslationTest(FunctionalTest):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def test_enter_questionnaire_in_spanish_freetext(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to the form to enter a new Questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))

        # She changes the language to Spanish
        self.changeLanguage('es')

        # She starts editing and enters some freetext
        self.click_edit_section('cat_1')
        self.findBy('name', 'qg_1-0-original_key_1').send_keys(
            'Foo content in Spanish')

        # She submits the step and sees the values were transmitted correctly.
        self.submit_form_step()
        self.findBy(
            'xpath', '//*[text()[contains(.,"Foo content in Spanish")]]')

        # She changes the language to English and sees that she can see the
        # freetext values, even though they are in Spanish
        self.changeLanguage('en')
        self.findBy(
            'xpath', '//*[text()[contains(.,"Foo content in Spanish")]]')

        self.click_edit_section('cat_1')

        # She sees that the field already contains the original value
        text_field = self.findBy('name', 'qg_1-0-translation_key_1')
        self.assertEqual(
            text_field.get_attribute('value'), 'Foo content in Spanish')

        # She changes the value to its English translation
        text_field.clear()
        text_field.send_keys('Foo content in English')

        # She submits the step
        self.submit_form_step()
        self.findBy(
            'xpath', '//*[text()[contains(.,"Foo content in English")]]')

        # She submits the Questionnaire
        self.review_action('submit')
        self.findBy(
            'xpath', '//*[text()[contains(.,"Foo content in English")]]')

        # She sees that the Spanish original is still there
        self.changeLanguage('es')
        self.findBy(
            'xpath', '//*[text()[contains(.,"Foo content in Spanish")]]')
