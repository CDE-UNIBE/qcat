from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from accounts.client import Typo3Client
from functional_tests.base import FunctionalTest
from sample.tests.test_views import route_questionnaire_new

route_add_module = 'sample:add_module'


@override_settings(IS_ACTIVE_FEATURE_MODULE=True)
@patch.object(Typo3Client, 'get_user_id')
class EditModuleTest(FunctionalTest):

    fixtures = [
        'groups_permissions.json', 'global_key_values.json', 'sample.json',
        'samplemodule.json'
    ]

    def test_edit_module(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She creates a sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        self.click_edit_section('cat_1')
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.findBy('xpath', '//div[@id="id_qg_3_0_key_4_chosen"]').click()
        self.findBy('xpath',
                    '//div[@id="id_qg_3_0_key_4_chosen"]//'
                    'ul[@class="chosen-results"]/li[text()="Germany"]').click()
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        sample_url = self.browser.current_url

        # She adds a module for this questionnaire
        self.toggle_all_sections()
        self.findBy('xpath', '//a[contains(@class, "js-show-embedded-modules-form")]').click()
        samplemodule_radio = self.findBy(
            'xpath',
            '//input[@value="samplemodule" and @name="module"]')
        samplemodule_radio.click()
        self.findBy('xpath', '//input[@type="submit" and @value="Create"]').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        module_url = self.browser.current_url

        # She sees the inherited values
        self.toggle_all_sections()
        self.findBy('xpath', '//*[text()[contains(.,"Key 1 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')

        # She edits the first step of the module
        self.click_edit_section('modcat_1')

        # She sees the inherited values as disabled fields
        key_1 = self.findBy('name', 'modqg_sample_01-0-original_key_1')
        self.assertEqual(key_1.get_attribute('value'), 'Foo')
        self.assertEqual(key_1.get_attribute('disabled'), 'true')

        key_4 = self.findBy('name', 'modqg_sample_02-0-key_4')
        self.assertEqual(key_4.get_attribute('disabled'), 'true')
        key_4_selected = self.findBy(
            'xpath', '//select[@name="modqg_sample_02-0-key_4"]/option[@selected]')
        self.assertEqual(key_4_selected.get_attribute('value'), 'country_2')

        # She sees she can edit the first question
        modkey_1 = self.findBy('name', 'modqg_01-0-original_modkey_01')
        self.assertIsNone(modkey_1.get_attribute('disabled'))

        # She goes to the sample questionnaire
        self.browser.get(sample_url)
        self.toggle_all_sections()

        # She edits some values
        self.click_edit_section('cat_1')
        self.findBy('name', 'qg_1-0-original_key_1').send_keys(' (changed)')
        self.findBy('xpath', '//div[@id="id_qg_3_0_key_4_chosen"]').click()
        self.findBy('xpath',
                    '//div[@id="id_qg_3_0_key_4_chosen"]//'
                    'ul[@class="chosen-results"]/li[text()="Switzerland"]').click()
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She goes back to the module and sees the updated values
        self.browser.get(module_url)
        self.toggle_all_sections()
        self.findBy('xpath', '//*[text()[contains(.,"Key 1 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo (changed)")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Switzerland")]]')

        # She enters the first question and saves the step
        self.click_edit_section('modcat_1')
        self.findBy('name', 'modqg_01-0-original_modkey_01').send_keys('asdf')
        self.submit_form_step()

        # She sees the inherited values and the first question
        self.findBy('xpath', '//*[text()[contains(.,"Key 1 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo (changed)")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Switzerland")]]')
        self.findBy('xpath', '//*[text()[contains(.,"ModKey 1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"asdf")]]')

        # She goes back to the form and sees all values
        self.click_edit_section('modcat_1')
        key_1 = self.findBy('name', 'modqg_sample_01-0-original_key_1')
        self.assertEqual(key_1.get_attribute('value'), 'Foo (changed)')
        self.assertEqual(key_1.get_attribute('disabled'), 'true')
        key_4 = self.findBy('name', 'modqg_sample_02-0-key_4')
        self.assertEqual(key_4.get_attribute('disabled'), 'true')
        key_4_selected = self.findBy(
            'xpath',
            '//select[@name="modqg_sample_02-0-key_4"]/option[@selected]')
        self.assertEqual(key_4_selected.get_attribute('value'), 'country_4')

        # By some hack, she makes the inherited value editable and submits the
        # step
        self.set_input_value(key_1, 'spam')
        self.submit_form_step()

        # She sees the unchanged inherited values
        self.findBy('xpath', '//*[text()[contains(.,"Key 1 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo (changed)")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Switzerland")]]')
        self.findBy('xpath', '//*[text()[contains(.,"ModKey 1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"asdf")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"spam")]]')

        # She goes to the questionnaire and sees the same values there.
        self.browser.get(sample_url)
        self.findBy('xpath', '//*[text()[contains(.,"Key 1 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo (changed)")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4 (Samplemodule)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Switzerland")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"spam")]]')
