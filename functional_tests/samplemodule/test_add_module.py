from django.core.urlresolvers import reverse
from unittest.mock import patch

from django.test.utils import override_settings

from accounts.client import Typo3Client
from functional_tests.base import FunctionalTest
from questionnaire.models import Questionnaire, QuestionnaireLink
from sample.tests.test_views import route_questionnaire_new

route_add_module = 'sample:add_module'


@override_settings(IS_ACTIVE_FEATURE_MODULE=True)
@patch.object(Typo3Client, 'get_user_id')
class AddModuleTest(FunctionalTest):

    fixtures = [
        'groups_permissions.json', 'global_key_values.json', 'sample.json',
        'samplemodule.json'
    ]

    def test_add_module(self, mock_get_user_id):

        # Alice is not logged in. She sees that adding a module requires a login
        self.browser.get(self.live_server_url + reverse(route_add_module))
        self.findBy('xpath', '//input[@name="username"]')
        self.findByNot(
            'xpath', '//input[contains(@class, "link-search-field")]')

        # Alice logs in
        self.doLogin()

        # Again, she goes to the page to add a module
        self.browser.get(self.live_server_url + reverse(route_add_module))
        self.findByNot('xpath', '//input[@name="username"]')
        search_field = self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]')

        # Step 2 is not visible
        step_2 = self.findBy('id', 'modules-select-module')
        self.assertFalse(step_2.is_displayed())

        # She searches for a sample questionnaire which does not exist
        search_field.send_keys('Foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="No results found"]')\
            .click()

        # Step 2 is still not visible
        self.assertFalse(step_2.is_displayed())

        # She creates a sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))

        self.click_edit_section('cat_1')
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She goes back to the page to add a module
        self.browser.get(self.live_server_url + reverse(route_add_module))
        search_field = self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]')

        # Step 2 is not visible
        step_2 = self.findBy('id', 'modules-select-module')
        self.assertFalse(step_2.is_displayed())

        # Step 3 is not visible
        step_3 = self.findBy('id', 'modules-create')
        self.assertFalse(step_3.is_displayed())

        # She searches for the created questionnaire and selects the Q
        search_field.send_keys('Foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"'
            ']').click()

        # Step 2 is now visible
        self.assertTrue(step_2.is_displayed())

        # Step 3 is hidden
        self.assertFalse(step_3.is_displayed())

        # The preview of the link is displayed
        self.findBy(
            'xpath',
            '//div[contains(@class, "link-preview")]/div[text()="Foo"]')

        # She removes the selected questionnaire again
        self.findBy(
            'xpath',
            '//div[contains(@class, "link-preview")]/div[text()="Foo"]/'
            'a[contains(@class, "close")]').click()
        self.findByNot(
            'xpath',
            '//div[contains(@class, "link-preview")]/div[text()="Foo"]')

        # Step 2 is hidden again
        self.assertFalse(step_2.is_displayed())

        # Step 3 is still hidden
        self.assertFalse(step_3.is_displayed())

        # She reselects the questionnaire
        search_field.send_keys('Foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"'
            ']').click()

        # Step 2 is visible again and the preview is displayed
        self.assertTrue(step_2.is_displayed())
        self.findBy(
            'xpath',
            '//div[contains(@class, "link-preview")]/div[text()="Foo"]')

        # Step 3 is still hidden
        self.assertFalse(step_3.is_displayed())

        # She selects the samplemodule module
        samplemodule_radio = self.findBy(
            'xpath',
            '//input[@value="samplemodule" and @name="module"]')
        samplemodule_radio.click()

        # She sees that step 3 is now visible.
        self.assertTrue(step_3.is_displayed())

        # She deselects the module and step 3 is hidden again
        samplemodule_radio.click()
        self.assertFalse(step_3.is_displayed())

        # She selects the module again - step 3 is shown again
        samplemodule_radio.click()
        self.assertTrue(step_3.is_displayed())

        # She removes the questionnaire and sees that step 2 and 3 are both
        # hidden again
        self.findBy(
            'xpath',
            '//div[contains(@class, "link-preview")]/div[text()="Foo"]/'
            'a[contains(@class, "close")]').click()
        self.assertFalse(step_2.is_displayed())
        self.assertFalse(step_3.is_displayed())

        # She selects everything again
        search_field.send_keys('Foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"'
            ']').click()
        samplemodule_radio = self.findBy(
            'xpath',
            '//input[@value="samplemodule" and @name="module"]')
        samplemodule_radio.click()

        self.assertEqual(Questionnaire.objects.count(), 1)
        self.assertEqual(QuestionnaireLink.objects.count(), 0)

        # She creates the link
        self.findBy('xpath', '//input[@type="submit"]').click()

        # She sees that she has been directed to the page to enter a new
        # samplemodule and she sees a success message.
        self.findBy('xpath', '//div[contains(@class, "is-samplemodule")]')
        self.findBy(
            'xpath',
            '//h1[contains('
            '@class, "tech-output-title") and text()="SAMPLEMODULE"]')
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # The samplemodule questionnaire has already been created
        self.assertEqual(Questionnaire.objects.count(), 2)

        # There is a link between the questionnaire and the module
        self.assertEqual(QuestionnaireLink.objects.count(), 2)

        # She goes back to the page to add a module and tries to create the
        # module to the same questionnaire again.
        self.browser.get(self.live_server_url + reverse(route_add_module))
        search_field = self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]')
        search_field.send_keys('Foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"'
            ']').click()

        # She sees step 2 but does not see a radio button for the module.
        step_2 = self.findBy('id', 'modules-select-module')
        self.assertTrue(step_2.is_displayed())
        self.findByNot(
            'xpath',
            '//input[@value="samplemodule" and @name="module"]')
