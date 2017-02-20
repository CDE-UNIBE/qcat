from accounts.middleware import WocatAuthenticationMiddleware
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.test.utils import override_settings
from selenium.webdriver.common.action_chains import ActionChains  # noqa
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from unittest.mock import patch

from accounts.models import User
from functional_tests.base import FunctionalTest
from sample.tests.test_views import (
    route_questionnaire_details,
    route_questionnaire_list,
    route_questionnaire_new,
    route_questionnaire_new_step,
    get_category_count,
)
from samplemulti.tests.test_views import route_questionnaire_details as \
    route_questionnaire_details_samplemulti
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices

TEST_INDEX_PREFIX = 'qcat_test_prefix_'

@patch.object(WocatAuthenticationMiddleware, 'process_request')
@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class QuestionnaireTest(FunctionalTest):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def test_translation(self, mock_process_request):

        # Alice logs in
        self.doLogin()

        # She goes to the form and sees the categories in English
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        self.checkOnPage('English')
        self.findBy('xpath', '//h2[contains(text(), "Category 1")]')

        # She changes the language to Spanish and sees the translated
        # categories
        self.changeLanguage('es')
        self.checkOnPage('Español')
        self.checkOnPage('English')

        # She changes the language to French and sees there is no
        # translation but the original English categories are displayed
        self.changeLanguage('fr')
        self.checkOnPage('Français')
        self.checkOnPage('English')

    # def test_numbered_questiongroups(self):
    #
    #     # Alice logs in
    #     self.doLogin()
    #
    #     # She goes to a step of the questionnaire
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_3'}))
    #
    #     # She sees that the Questiongroup with Key 9 is numbered
    #     fieldset = self.findBy('xpath', '//fieldset[@class="row"][2]')
    #
    #     numbered_1 = self.findBy(
    #         'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
    #         ')])[1]', base=fieldset)
    #     self.assertEqual(numbered_1.text, '1:')
    #     numbered_2 = self.findBy(
    #         'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
    #         ')])[2]', base=fieldset)
    #     self.assertEqual(numbered_2.text, '2:')
    #
    #     # She enters some data for the Keys 9
    #     self.findBy('id', 'id_qg_7-0-original_key_9').send_keys(
    #         'This is the first key')
    #     self.findBy('id', 'id_qg_7-1-original_key_9').send_keys('Second key')
    #
    #     # She submits the step and sees the values are presented in the
    #     # correct order in the overview
    #     self.findBy('id', 'button-submit').click()
    #     res = self.findManyBy(
    #         'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
    #
    #     self.assertEqual(len(res), 2)
    #     self.assertIn('This is the first key', res[0].text)
    #     self.assertIn('Second key', res[1].text)
    #
    #     # She starts editing again and sees that the keys are displayed
    #     # in the correct order
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_3'}))
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_7-0-original_key_9" and @value="This '
    #         'is the first key"]')
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_7-1-original_key_9" and @value="'
    #         'Second key"]')
    #
    #     fieldset = self.findBy('xpath', '//fieldset[@class="row"][2]')
    #
    #     # She changes the order of the keys by drag-and-drop
    #     el_1 = self.findBy(
    #         'xpath', '//fieldset[@class="row"][2]//p[contains(@class, '
    #         '"questiongroup-numbered-number")][1]',
    #         base=fieldset)
    #     ActionChains(self.browser).click_and_hold(
    #         on_element=el_1).move_by_offset(0, 100).release().perform()
    #
    #     # She submits the step and sees the values are presented in the
    #     # correct order in the overview
    #     self.findBy('id', 'button-submit').click()
    #
    #     res = self.findManyBy(
    #         'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
    #     self.assertEqual(len(res), 2)
    #     self.assertIn('Second key', res[0].text)
    #     self.assertIn('This is the first key', res[1].text)
    #
    #     # She goes back to the form and sees the order persists
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_3'}))
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_7-0-original_key_9" and @value="'
    #         'Second key"]')
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_7-1-original_key_9" and @value="'
    #         'This is the first key"]')
    #
    #     # She submits the step and the entire questionnaire
    #     self.findBy('id', 'button-submit').click()
    #     self.findBy('id', 'button-submit').click()
    #
    #     # She sees that the values were submitted correctly
    #     self.findBy('xpath', '//div[contains(@class, "success")]')
    #     res = self.findManyBy(
    #         'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
    #     self.assertEqual(len(res), 2)
    #     self.assertIn('Second key', res[0].text)
    #     self.assertIn('This is the first key', res[1].text)

    # def test_numbered_questiongroups_2(self):
    #
    #     # Alice logs in
    #     self.doLogin()
    #
    #     # She goes to a step of the questionnaire
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_3'}))
    #
    #     # She sees that the Questiongroup with Keys 17 and 18 is numbered
    #     fieldset = self.findBy('xpath', '//fieldset[@class="row"][1]')
    #
    #     numbered_1 = self.findBy(
    #         'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
    #         ')])[1]', base=fieldset)
    #     self.assertEqual(numbered_1.text, '1:')
    #     numbered_2 = self.findBy(
    #         'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
    #         ')])[2]', base=fieldset)
    #     self.assertEqual(numbered_2.text, '2:')
    #
    #     # She enters some data for the Keys 17 and 18
    #     self.findBy('id', 'id_qg_13-0-original_key_17').send_keys('Key 17 - 1')
    #     self.findBy('id', 'id_qg_13-0-original_key_18').send_keys('Key 18 - 1')
    #     self.findBy('id', 'id_qg_13-1-original_key_17').send_keys('Key 17 - 2')
    #     self.findBy('id', 'id_qg_13-1-original_key_18').send_keys('Key 18 - 2')
    #
    #     # She submits the step and sees the values are presented in the
    #     # correct order in the overview
    #     self.findBy('id', 'button-submit').click()
    #     res = self.findManyBy(
    #         'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
    #     self.assertEqual(len(res), 2)
    #     self.assertIn('Key 17 - 1', res[0].text)
    #     self.assertIn('Key 18 - 1', res[0].text)
    #     self.assertIn('Key 17 - 2', res[1].text)
    #     self.assertIn('Key 18 - 2', res[1].text)
    #
    #     # She starts editing again and sees that the keys are displayed
    #     # in the correct order
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_3'}))
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_13-0-original_key_17" and '
    #         '@value="Key 17 - 1"]')
    #     self.findBy(
    #         'xpath', '//textarea[@id="id_qg_13-0-original_key_18" and '
    #         'text()="Key 18 - 1"]')
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_13-1-original_key_17" and '
    #         '@value="Key 17 - 2"]')
    #     self.findBy(
    #         'xpath', '//textarea[@id="id_qg_13-1-original_key_18" and '
    #         'text()="Key 18 - 2"]')
    #
    #     self.findByNot(
    #         'xpath', '//input[@id="id_qg_13-2-original_key_17"]')
    #
    #     # She adds another questiongroup
    #     self.findBy(
    #         'xpath', '//fieldset[@class="row"][1]//div[contains(@class, '
    #         '"questiongroup")][3]//a[contains(text(), "Add More")]').click()
    #
    #     # The new questiongroup has the number 3:
    #     fieldset = self.findBy('xpath', '//fieldset[@class="row"][1]')
    #     numbered_3 = self.findBy(
    #         'xpath', '//fieldset[@class="row"][1]//div[contains(@class, '
    #         '"questiongroup")][3]/div[contains(@class, "row")][3]//p['
    #         'contains(@class, "questiongroup-numbered-number")]')
    #     self.assertEqual(numbered_3.text, '3:')
    #
    #     # She adds some content to the 3rd questiongroup
    #     self.findBy('id', 'id_qg_13-2-original_key_17').send_keys('Key 17 - 3')
    #     self.findBy('id', 'id_qg_13-2-original_key_18').send_keys('Key 18 - 3')
    #
    #     # She also decides to change the order
    #     el_1 = self.findBy(
    #         'xpath', '//fieldset[@class="row"][1]/div[contains(@class, '
    #         '"questiongroup")][3]/div[contains(@class, "row")][2]//p['
    #         'contains(@class, "questiongroup-numbered-number")]')
    #     ActionChains(self.browser).click_and_hold(
    #         on_element=el_1).move_by_offset(0, -200).release().perform()
    #
    #     # She submits the step and sees the values are presented in the
    #     # correct order in the overview
    #     self.findBy('id', 'button-submit').click()
    #     res = self.findManyBy(
    #         'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
    #     self.assertEqual(len(res), 3)
    #     self.assertIn('Key 17 - 2', res[0].text)
    #     self.assertIn('Key 18 - 2', res[0].text)
    #     self.assertIn('Key 17 - 1', res[1].text)
    #     self.assertIn('Key 18 - 1', res[1].text)
    #     self.assertIn('Key 17 - 3', res[2].text)
    #     self.assertIn('Key 18 - 3', res[2].text)
    #
    #     # She goes back to the form and sees the order persists
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_3'}))
    #
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_13-0-original_key_17" and '
    #         '@value="Key 17 - 2"]')
    #     self.findBy(
    #         'xpath', '//textarea[@id="id_qg_13-0-original_key_18" and '
    #         'text()="Key 18 - 2"]')
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_13-1-original_key_17" and '
    #         '@value="Key 17 - 1"]')
    #     self.findBy(
    #         'xpath', '//textarea[@id="id_qg_13-1-original_key_18" and '
    #         'text()="Key 18 - 1"]')
    #     self.findBy(
    #         'xpath', '//input[@id="id_qg_13-2-original_key_17" and '
    #         '@value="Key 17 - 3"]')
    #     self.findBy(
    #         'xpath', '//textarea[@id="id_qg_13-2-original_key_18" and '
    #         'text()="Key 18 - 3"]')
    #
    #     # She submits the step and the entire questionnaire
    #     self.findBy('id', 'button-submit').click()
    #     self.findBy('id', 'button-submit').click()
    #
    #     # She sees that the values were submitted correctly
    #     self.findBy('xpath', '//div[contains(@class, "success")]')
    #     res = self.findManyBy(
    #         'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
    #     self.assertEqual(len(res), 3)
    #     self.assertIn('Key 17 - 2', res[0].text)
    #     self.assertIn('Key 18 - 2', res[0].text)
    #     self.assertIn('Key 17 - 1', res[1].text)
    #     self.assertIn('Key 18 - 1', res[1].text)
    #     self.assertIn('Key 17 - 3', res[2].text)
    #     self.assertIn('Key 18 - 3', res[2].text)

    def test_repeating_questiongroups(self, mock_process_request):
        mock_process_request.return_value = None

        initial_button_count = 4

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))
        self.rearrangeFormHeader()

        # She sees the helptext
        self.checkOnPage('Helptext 1')

        # She sees many buttons to add more questions
        add_more_buttons = self.findManyBy(
            'xpath', '//a[@data-questiongroup-keyword]')
        self.assertEqual(len(add_more_buttons), initial_button_count)

        # She sees the first questiongroups which has no possibility to
        # add more questions
        self.findBy('name', 'qg_5-0-original_key_7')
        self.findByNot('name', 'qg_5-1-original_key_7')

        # The second questiongroup is shown only once but can be
        # repeated up to 3 times
        self.findBy('name', 'qg_6-0-original_key_8').send_keys('1')
        self.findByNot('name', 'qg_6-1-original_key_8')

        btn_add_more_qg_6 = self.findBy(
            'xpath', '//a[@data-questiongroup-keyword="qg_6"]')
        self.assertTrue(btn_add_more_qg_6.is_displayed())

        # She adds another one and sees there is a remove button
        btn_add_more_qg_6.click()
        self.assertTrue(btn_add_more_qg_6.is_displayed())
        self.findBy('name', 'qg_6-1-original_key_8').send_keys('2')
        self.findByNot('name', 'qg_6-2-original_key_8')
        remove_buttons = self.findManyBy(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')
        self.assertEqual(len(remove_buttons), 2)

        # And yet another one. The maximum is reached and the button to add
        # one more is hidden.
        btn_add_more_qg_6.click()
        self.assertFalse(btn_add_more_qg_6.is_displayed())
        self.findBy('name', 'qg_6-1-original_key_8')
        self.findBy('name', 'qg_6-2-original_key_8').send_keys('3')
        remove_buttons = self.findManyBy(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')
        self.assertEqual(len(remove_buttons), 3)

        # She removes the middle one and sees that the correct one is
        # removed and the names of the other ones are updated.
        remove_buttons[1].click()
        f1 = self.findBy('name', 'qg_6-0-original_key_8')
        self.assertEqual(f1.get_attribute('value'), '1')
        f2 = self.findBy('name', 'qg_6-1-original_key_8')
        self.assertEqual(f2.get_attribute('value'), '3')
        self.findByNot('name', 'qg_6-2-original_key_8')
        remove_buttons = self.findManyBy(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')
        self.assertEqual(len(remove_buttons), 2)

        # She removes the first one and sees that only one remains with
        # no button to remove it
        remove_buttons[0].click()
        f1 = self.findBy('name', 'qg_6-0-original_key_8')
        self.assertEqual(f1.get_attribute('value'), '3')
        self.findByNot('name', 'qg_6-1-original_key_8')
        self.findByNot('name', 'qg_6-2-original_key_8')
        self.findByNot(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')

        # The third questiongroup appears two times but has no buttons
        self.findBy('name', 'qg_7-0-original_key_9').send_keys('a')
        self.findBy('name', 'qg_7-1-original_key_9').send_keys('b')

        # The fourth questiongroup has two minimum fields and maximum 3
        self.findBy('name', 'qg_8-0-original_key_10').send_keys('x')
        self.findBy('name', 'qg_8-1-original_key_10').send_keys('y')
        self.findByNot('name', 'qg_8-2-original_key_10')

        # She adds one questiongroup and sees the button to remove it 3 times.
        btn_add_more_qg_8 = self.findBy(
            'xpath', '//a[@data-questiongroup-keyword="qg_8"]')
        btn_add_more_qg_8.click()
        self.findBy('name', 'qg_8-2-original_key_10').send_keys('z')
        remove_buttons = self.findManyBy(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')
        self.assertEqual(len(remove_buttons), 3)

        # The button to add another one is not visible anymore
        self.assertFalse(btn_add_more_qg_8.is_displayed())

        # She submits the form
        self.findBy('id', 'button-submit').click()

        # She sees the values were submitted
        self.findBy('xpath', '//*[text()[contains(.,"Key 8")]]')
        self.assertEqual(len(self.findManyBy(
            'xpath', '//*[text()[contains(.,"Key 9")]]')), 2)
        self.assertEqual(len(self.findManyBy(
            'xpath', '//*[text()[contains(.,"Key 10")]]')), 3)

        # She edits again
        self.click_edit_section('cat_3')

        # Key 8 is there only once
        f1 = self.findBy('name', 'qg_6-0-original_key_8')
        self.assertEqual(f1.get_attribute('value'), '3')
        self.findByNot('name', 'qg_6-1-original_key_8')
        self.findByNot('name', 'qg_6-2-original_key_8')

        # Key 10 is there 3 times
        f1 = self.findBy('name', 'qg_8-0-original_key_10')
        self.assertEqual(f1.get_attribute('value'), 'x')
        f2 = self.findBy('name', 'qg_8-1-original_key_10')
        self.assertEqual(f2.get_attribute('value'), 'y')
        f3 = self.findBy('name', 'qg_8-2-original_key_10')
        self.assertEqual(f3.get_attribute('value'), 'z')

        # The button to add onther one is not visible
        btn_add_more_qg_8 = self.findBy(
            'xpath', '//a[@data-questiongroup-keyword="qg_8"]')
        self.assertFalse(btn_add_more_qg_8.is_displayed())

        # She removes one Key 10 and submits the form again
        remove_buttons = self.findManyBy(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')
        self.assertEqual(len(remove_buttons), 3)
        remove_buttons[0].click()
        self.findByNot(
            'xpath',
            '//a[@data-remove-this and not(contains(@style,"display: none"))]')

        self.findBy('id', 'button-submit').click()
        self.review_action('submit')

    def test_form_progress(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes directly to the Sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))

        # She sees that all progress bars are to 0%
        progress_indicators = self.findManyBy(
            'xpath',
            '//div[@class="tech-section-progress"]/span[@class="steps"]')
        self.assertEqual(len(progress_indicators), get_category_count())
        for x in progress_indicators:
            self.assertIn('0/', x.text)
        progress_bars = self.findManyBy(
            'xpath', '//span[@class="meter" and @style="width:0%"]')
        self.assertEqual(len(progress_bars), len(progress_indicators))

        # She goes to the first category and sees another progress bar
        self.click_edit_section('cat_1')
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
        completed_steps = self.findBy('class_name', 'progress-completed')
        self.assertEqual(completed_steps.text, '0')
        total_steps = self.findBy('class_name', 'progress-total')
        self.assertEqual(total_steps.text, '2')

        # She types something in the first field and sees that the
        # progress bar changed
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('')
        self.findByNot('xpath', '//span[@class="meter" and @style="width:0%"]')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        completed_steps = self.findBy('class_name', 'progress-completed')
        self.assertEqual(completed_steps.text, '1')

        # She saves the step and sees that the progress bar on the
        # overview page has changed
        self.findBy('id', 'button-submit').click()
        progress_bars = self.findManyBy(
            'xpath', '//span[@class="meter" and @style="width:0%"]')
        self.assertEqual(len(progress_bars), get_category_count() - 1)
        progress_bars = self.findBy(
            'xpath', '//span[@class="meter" and @style="width:50%"]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[2]/span[@class="steps"]')
        self.assertIn('1/2', progress_indicator.text)

        # She decides to edit the step again and deletes what she
        # entered. She notices that the bar is back to 0, also on the
        # overview page.
        self.click_edit_section('cat_1')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 0%;"]')
        self.findBy('id', 'button-submit').click()

        progress_indicators = self.findManyBy(
            'xpath',
            '//div[@class="tech-section-progress"]/span[@class="steps"]')
        self.assertEqual(len(progress_indicators), get_category_count())
        for x in progress_indicators:
            self.assertIn('0/', x.text)
        progress_bars = self.findManyBy(
            'xpath', '//span[@class="meter" and @style="width:0%"]')
        self.assertEqual(len(progress_bars), len(progress_indicators))

        # She sees that step 0 has only 2 categories listed, although it
        # contains 3 (a subcategory which has no content)
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[1]/span[@class="steps"]')
        self.assertIn('0/2', progress_indicator.text)

        # She finally goes to step 0 of the questionnaire and also there, sees a
        # subcategory with no content and she notices it is not counted for the
        # progress
        self.click_edit_section('cat_0')
        self.findBy('xpath', '//legend[contains(text(), "Subcategory 0_1")]')
        self.findBy('xpath', '//legend[contains(text(), "Subcategory 0_2")]')
        self.findBy('xpath', '//legend[contains(text(), "Subcategory 0_3")]')
        completed_steps = self.findBy('class_name', 'progress-completed')
        self.assertEqual(completed_steps.text, '0')
        total_steps = self.findBy('class_name', 'progress-total')
        self.assertEqual(total_steps.text, '2')
        self.findBy('name', 'qg_31-0-original_key_45').send_keys('foo')
        self.findBy('name', 'qg_31-0-original_key_46').send_keys('bar')
        completed_steps = self.findBy('class_name', 'progress-completed')
        self.assertEqual(completed_steps.text, '1')
        total_steps = self.findBy('class_name', 'progress-total')
        self.assertEqual(total_steps.text, '2')

    def test_textarea_maximum_length(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        # She tries to enter a lot of characters to Key 2, which is
        # limited to 50 chars. Only the first 50 characters are entered
        key_2 = self.findBy('id', 'id_qg_2-0-original_key_2')
        key_2.send_keys("x" * 60)
        self.assertEqual(key_2.get_attribute('value'), "x" * 50)

        # She sees that the textarea is only 2 rows high
        self.assertEqual(int(key_2.get_attribute('rows')), 2)

        # She tries to enter a huge amount of characters to Key 6 which
        # has a default max_length of 500. Again, only the first 500
        # characters are entered.
        # key_6 = self.findBy('id', 'id_qg_3-0-original_key_6')
        # key_6.send_keys("x" * 600)
        # self.assertEqual(key_6.get_attribute('value'), "x" * 500)

        # # She sees that the textarea is by default 10 rows high
        # self.assertEqual(int(key_6.get_attribute('rows')), 10)

        # She tries the same with the first Key 3, a textfield with 50
        # chars limit
        key_3_1 = self.findBy('id', 'id_qg_1-0-original_key_3')
        key_3_1.send_keys("x" * 60)
        self.assertEqual(key_3_1.get_attribute('value'), "x" * 50)

        # # The second Key 3 is a textfield with the default limit of 200
        # key_3_2 = self.findBy('id', 'id_qg_2-0-original_key_3')
        # key_3_2.send_keys("x" * 210)
        # self.assertEqual(key_3_2.get_attribute('value'), "x" * 200)

        # By some hack, she enters more values than allowed in Key 2 and
        # she tries to submit the form
        self.browser.execute_script(
            "document.getElementById('id_qg_2-0-original_key_2')."
            "value='{}'".format("x" * 600))
        self.findBy('id', 'button-submit').click()

        # She sees an error message and the form was not submitted
        self.findBy('xpath', '//div[contains(@class, "alert")]')

        # She enters an accepted amount of characters and can submit the
        # form completely
        self.findBy('id', 'id_qg_2-0-original_key_2').clear()
        self.findBy('id', 'id_qg_2-0-original_key_2').send_keys("x" * 60)
        self.submit_form_step()
        self.review_action('submit')

    def test_textarea_preserves_line_breaks(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        # She enters some value for Key 2 with linebreaks
        textarea = self.findBy('id', 'id_qg_2-0-original_key_2')
        textarea.send_keys('asdf')
        textarea.send_keys(Keys.RETURN)
        textarea.send_keys('asdf')

        # She submits the form
        self.submit_form_step()
        self.wait_for('xpath', '//p[contains(text(), "asdf")]')

        # She sees the values were submitted with linebreaks
        self.findBy('xpath', '//*[contains(text(), "Key 2")]')
        details = self.findBy('xpath', '//p[contains(text(), "asdf")]')
        self.assertEqual(details.text, 'asdf\nasdf')

        self.review_action('submit')

    def test_nested_subcategories(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))

        # She sees values which are inside nested subcategories
        self.findBy('id', 'id_qg_19-0-original_key_5')
        self.findBy('id', 'id_qg_20-0-original_key_25')
        self.findBy('id', 'id_qg_21-0-original_key_26')

        # She sees the progress is at 0
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees that no values were submitted
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 25")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 26")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[3]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the step and fills out some fields
        self.click_edit_section('cat_2')
        self.findBy('id', 'id_qg_19-0-original_key_5').send_keys('Foo')
        self.findBy('id', 'id_qg_20-0-original_key_25').send_keys('')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 25%;"]')
        self.findBy('id', 'id_qg_21-0-original_key_26').send_keys('Bar')
        self.findBy('id', 'id_qg_20-0-original_key_25').send_keys('')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees the values were submitted
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 26")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 25")]]')

        # She sees that value to key 25 was only submitted once
        key_26 = self.findManyBy('xpath', '//*[text()[contains(.,"Key 26")]]')
        self.assertEqual(len(key_26), 1)

        # She goes back to the form and sees that the values are populated
        # correctly in the form
        self.click_edit_section('cat_2')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.assertEqual(self.findBy(
            'id', 'id_qg_19-0-original_key_5').get_attribute('value'), 'Foo')
        self.assertEqual(self.findBy(
            'id', 'id_qg_21-0-original_key_26').get_attribute('value'), 'Bar')
        self.findBy('id', 'id_qg_20-0-original_key_25').send_keys('Faz')

        # She submits the form and sees the values were submitted
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 26")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 25")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')

        # She submits the form completely and sees the values were submitted
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 26")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 25")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')

    def test_selects_with_chosen(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        # She sees Key 4, which is a select, rendered with Chosen.
        # Initially, no value is selected.
        self.findBy('xpath', '//select[@name="qg_3-0-key_4"]')
        chosen_field = self.findBy('xpath', '//a[@class="chosen-single"]')
        self.assertEqual(chosen_field.text, '-')

        # She sees that the values are ordered alphabetically
        values = ['Afghanistan', 'Cambodia', 'Germany', 'Switzerland']
        for i, v in enumerate(values):
            self.findBy(
                'xpath',
                '//select[@name="qg_3-0-key_4"]/option[{}][contains(text(),'
                ' "{}")]'.format(i + 2, v))

        # She sees that the form progress is at 0
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees that no value was submitted,
        # progress of Category 1 is still 0
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 4")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[2]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and no value is selected
        self.click_edit_section('cat_1')
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
        self.findBy('xpath', '//select[@name="qg_3-0-key_4"]')
        chosen_field = self.findBy('xpath', '//a[@class="chosen-single"]')
        self.assertEqual(chosen_field.text, '-')

        # She sees that she can select a Value by mouse click
        self.findBy(
            'xpath', '//div[contains(@class, "chosen-container")]').click()
        self.findBy(
            'xpath', '//ul[@class="chosen-results"]/li[text()="Afghanistan"]')\
            .click()
        self.assertEqual(chosen_field.text, 'Afghanistan')

        # She sees that the form progress was updated
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees that the value was submitted,
        # progress of Category 1 is now updated
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Afghanistan")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[2]/span[@class="steps"]')
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the form and sees that the value is still selected
        # and the progress is updated
        self.click_edit_section('cat_1')
        self.findBy('xpath', '//select[@name="qg_3-0-key_4"]')
        chosen_field = self.findBy('xpath', '//a[@class="chosen-single"]')
        self.assertEqual(chosen_field.text, 'Afghanistan')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She selects another value, sees that the form progress is still at
        # the same value
        self.findBy(
            'xpath', '//div[contains(@class, "chosen-container")]').click()
        self.findBy(
            'xpath', '//ul[@class="chosen-results"]/li[text()="Germany"]')\
            .click()
        self.assertEqual(chosen_field.text, 'Germany')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees the value was updated
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')

        # She submits the entire form and sees the value is on the details page
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')

    def test_selects_with_chosen_repeating(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))
        self.rearrangeFormHeader()

        # She clicks the button to add a non-registered person
        create_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="create"]')
        create_radio.click()

        # She sees Key 4, which is a select, rendered with Chosen.
        # Initially, no value is selected.
        self.findBy('xpath', '//select[@name="qg_31-0-key_4"]')
        chosen_fields = self.findManyBy('xpath', '//div[contains(@class, "form-user-tab-create")]//a[@class="chosen-single"]')
        self.assertEqual(len(chosen_fields), 1)
        self.assertEqual(chosen_fields[0].text, '-')

        # She sees that she can select a Value by mouse click
        self.findBy(
            'xpath', '//div[contains(@class, "form-user-tab-create")]//a[@class="chosen-single"]').click()
        self.findBy(
            'xpath', '//ul[@class="chosen-results"]/li[text()="Afghanistan"]') \
            .click()
        self.assertEqual(chosen_fields[0].text, 'Afghanistan')

        # She adds another questiongroup
        self.findBy('xpath', '//a[@data-questiongroup-keyword="qg_31"]').click()

        # She clicks the tab to add a non-registered person
        create_radios = self.findManyBy(
            'xpath', '//input[@name="form-user-radio" and @value="create"]')
        create_radios[1].click()
        # No idea why 2 clicks are necessary
        create_radios[1].click()

        # She sees another chosen field which is empty
        self.findBy('xpath', '//select[@name="qg_31-1-key_4"]')
        chosen_fields = self.findManyBy('xpath',
                                        '//div[contains(@class, "form-user-tab-create")]//a[@class="chosen-single"]')
        self.assertEqual(len(chosen_fields), 2)
        self.assertEqual(chosen_fields[0].text, 'Afghanistan')
        self.assertEqual(chosen_fields[1].text, '-')

        self.findBy('xpath', '//div[@id="id_qg_31_1_key_4_chosen"]').click()
        self.findBy('xpath', '//div[@id="id_qg_31_1_key_4_chosen"]//ul[@class="chosen-results"]/li[text()="Germany"]').click()
        chosen_fields = self.findManyBy('xpath',
                                        '//div[contains(@class, "form-user-tab-create")]//a[@class="chosen-single"]')
        self.assertEqual(len(chosen_fields), 2)
        self.assertEqual(chosen_fields[0].text, 'Afghanistan')
        self.assertEqual(chosen_fields[1].text, 'Germany')

        # She submits the form and sees the value was updated
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Afghanistan")]]')

        # She submits the entire form and sees the value is on the details page
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Afghanistan")]]')

    def test_checkbox(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))

        # She sees that no Checkbox of Key 13 is selected by default
        self.findByNot(
            'xpath', '//input[@name="qg_10-0-key_13" and @checked="checked"]')

        # She sees that the form progress is at 0
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees that no value was submitted,
        # progress of Category 2 is still 0
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 13")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[3]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and no checkbox is selected
        self.click_edit_section('cat_2')
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
        self.findByNot(
            'xpath', '//input[@name="qg_10-0-key_13" and @checked="checked"]')

        # She selects a first checkbox and sees that the form progress
        # was updated
        self.findBy(
            'xpath', '(//input[@name="qg_10-0-key_13"])[1]').click()
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 25%;"]')

        # She submits the step and sees that the value was submitted and
        # the form progress on the overview page is updated
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 13")]]')

        self.findBy('xpath', '//*[text()[contains(.,"Value 13_1")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[3]/span[@class="steps"]')
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the step and sees that the first checkbox is
        # selected, form progress is at 1
        self.click_edit_section('cat_2')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 25%;"]')

        # She deselects the first value and sees that the progress was
        # updated
        self.findBy(
            'xpath', '(//input[@name="qg_10-0-key_13"])[1]').click()
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 0%;"]')

        # She then selects the second and third values and submits the
        # form
        self.findBy(
            'xpath', '(//input[@name="qg_10-0-key_13"])[2]').click()
        self.findBy(
            'xpath', '(//input[@name="qg_10-0-key_13"])[3]').click()
        self.submit_form_step()

        # The overview now shows both values
        self.findBy('xpath', '//*[text()[contains(.,"Key 13")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Value 13_1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_2")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_3")]]')

        # She submits the form and sees that the radio value is stored
        # correctly
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 13")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Value 13_1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_2")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_3")]]')

    def test_checkbox_other(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.rearrangeFormHeader()

        # She sees there are checkboxes and one "other" checkbox with a
        # textfield
        cb_1 = self.findBy('id', 'id_qg_36-0-key_50_1_1')
        cb_2 = self.findBy('id', 'id_qg_36-0-key_50_1_2')
        other_cb = self.findBy(
            'xpath', '//label[@for="id_qg_36-0-original_key_51"]/input['
                     'contains(@class, "checkbox-other")]')
        other_textfield = self.findBy('id', 'id_qg_36-0-original_key_51')

        # She sees the textfield is readonly
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')

        # She selects the first checkbox, the other checkbox is still not
        # selected, the textfield readonly
        cb_1.click()
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')
        self.assertIsNone(other_cb.get_attribute('checked'))

        # She selects the other checkbox and sees she can now enter some text
        other_cb.click()
        self.assertEqual(other_cb.get_attribute('checked'), 'true')
        self.assertIsNone(other_textfield.get_attribute('readonly'))

        # She selects another checkbox
        cb_2.click()
        self.assertEqual(other_cb.get_attribute('checked'), 'true')
        self.assertIsNone(other_textfield.get_attribute('readonly'))

        # She enters some text
        other_textfield.send_keys('foo content')

        # She deselects the first checkbox
        cb_1.click()
        self.assertEqual(other_cb.get_attribute('checked'), 'true')
        self.assertIsNone(other_textfield.get_attribute('readonly'))
        self.assertEqual(other_textfield.get_attribute('value'), 'foo content')

        # She submits the step and sees the values are both submitted
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"foo content")]]')

        # She goes back to the form
        self.click_edit_section('cat_1')
        cb_1 = self.findBy('id', 'id_qg_36-0-key_50_1_1')
        cb_2 = self.findBy('id', 'id_qg_36-0-key_50_1_2')
        other_cb = self.findBy(
            'xpath', '//label[@for="id_qg_36-0-original_key_51"]/input['
                     'contains(@class, "checkbox-other")]')
        other_textfield = self.findBy('id', 'id_qg_36-0-original_key_51')

        # She sees the correct checkboxes are selected
        self.assertEqual(cb_2.get_attribute('checked'), 'true')
        self.assertEqual(other_cb.get_attribute('checked'), 'true')
        self.assertIsNone(other_textfield.get_attribute('readonly'))
        self.assertEqual(other_textfield.get_attribute('value'), 'foo content')

        # She deselects the other checkbox and sees the textfield is emptied
        other_cb.click()
        self.assertIsNone(other_cb.get_attribute('checked'))
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')
        self.assertEqual(other_textfield.get_attribute('value'), '')

        # She selects it again and enters some text
        other_cb.click()
        other_textfield.send_keys('foo bar')

        # She submits the step
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"foo bar")]]')

        # She submits the entire questionnaire
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"foo bar")]]')

    def test_image_checkbox(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))
        self.rearrangeFormHeader()

        # She sees that no Checkbox of Key 14 is selected by default
        self.findByNot(
            'xpath', '//input[@name="qg_11-0-key_14" and @checked="checked"]')

        # She sees that the form progress is at 0
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees that no value was submitted,
        # progress of Category 4 is still 0
        self.submit_form_step()
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 14")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[5]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "cat_4"))
        )
        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and no checkbox is selected
        self.click_edit_section('cat_4')
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
        self.findByNot(
            'xpath', '//input[@name="qg_11-0-key_14" and @checked="checked"]')

        # She selects a first checkbox and sees that the form progress
        # was updated
        self.findBy(
            'xpath', '//label[@for="id_qg_11-0-key_14_1"]').click()
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 16.6667%;"]')

        # She submits the step and sees that the value was submitted and
        # the form progress on the overview page is updated
        self.submit_form_step()
        self.findBy('xpath', '//img[@alt="Value 14_1"]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[5]/span[@class="steps"]')
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the step and sees that the first checkbox is
        # selected, form progress is at 1
        self.click_edit_section('cat_4')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 16.6667%;"]')

        # She deselects the first value and sees that the progress was
        # updated
        self.findBy(
            'xpath', '//label[@for="id_qg_11-0-key_14_1"]').click()
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 0%;"]')

        # She then selects the second and third values and submits the
        # form
        self.findBy(
            'xpath', '//label[@for="id_qg_11-0-key_14_2"]').click()
        self.findBy(
            'xpath', '//label[@for="id_qg_11-0-key_14_3"]').click()
        self.submit_form_step()

        # The overview now shows both values
        self.findByNot(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_1"]')
        self.findBy(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_2"]')
        self.findBy(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_3"]')

        # She submits the form and sees that the radio value is stored
        # correctly
        self.review_action('submit')
        self.findByNot(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_1"]')
        self.findBy(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_2"]')
        self.findBy(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_3"]')

    def test_measure_conditional(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))
        self.rearrangeFormHeader()

        # She sees the measure box for Key 21
        self.findBy(
            'xpath',
            '//div[@class="button-bar"]/ul/li/input[@name="qg_16-0-key_21"]')

        # She sees that Key 22 and Key 23 are not visible
        key_22 = self.findBy('xpath', '//label[@for="id_qg_17-0-key_22_1"]')
        key_23 = self.findBy('id', 'id_qg_17-0-original_key_23')
        self.assertFalse(key_22.is_displayed())
        self.assertFalse(key_23.is_displayed())

        # She selects measure 2 of Key 21
        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_2"]').click()

        # She sees that Keys 22 and 23 are now visible
        self.assertTrue(key_22.is_displayed())
        self.assertTrue(key_23.is_displayed())

        # She selects measure 1 of Key 21 and the Keys are hidden again.
        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_1"]').click()
        self.assertFalse(key_22.is_displayed())
        self.assertFalse(key_23.is_displayed())

        # She selects measure 2, selects a value of Key 22 and enters
        # some text for Key 23.
        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_2"]').click()
        key_22.click()
        key_23.send_keys('Foo')

        # She selects measure 1 and then 2 again and sees the previously
        # selected and entered values are gone.
        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_1"]').click()
        self.assertFalse(key_22.is_displayed())
        self.assertFalse(key_23.is_displayed())

        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_2"]').click()
        self.assertFalse(key_22.is_selected())
        self.assertEqual(key_23.get_attribute('value'), '')

        # She enters some data, submits the form and sees that all
        # values were submitted
        key_22.click()
        key_23.send_keys('Foo')
        self.submit_form_step()
        self.checkOnPage('Key 21')
        self.checkOnPage('medium')
        self.findBy('xpath', '//img[@alt="Value 16_1"]')
        self.checkOnPage('Key 23')
        self.checkOnPage('Foo')

        # She goes back to the form and sees that the values are still
        # there, Keys 22 and 23 are visible
        self.click_edit_section('cat_4')
        key_22 = self.findBy('xpath', '//label[@for="id_qg_17-0-key_22_1"]')
        key_23 = self.findBy('id', 'id_qg_17-0-original_key_23')
        self.assertTrue(key_22.is_displayed())
        self.assertTrue(key_23.is_displayed())

        # She unchecks Key 22
        key_22.click()
        self.assertTrue(key_22.is_displayed())

        # She unselects Key 21 and sees that everything is hidden again
        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_3"]').click()
        self.assertFalse(key_22.is_displayed())
        self.assertFalse(key_23.is_displayed())

        # She selects Key 21 again and sees it is empty again
        self.findBy('xpath', '//label[@for="id_qg_16-0-key_21_2"]').click()
        self.assertFalse(key_22.is_selected())
        self.assertEqual(key_23.get_attribute('value'), '')

        # She enters some values again and submits the form completely
        key_23.send_keys('Bar')
        self.submit_form_step()
        self.review_action('submit')

        self.checkOnPage('Key 21')
        self.checkOnPage('medium')
        self.checkOnPage('Key 23')
        self.checkOnPage('Bar')

    def test_checkbox_conditional(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))

        # She sees the checkbox (Value 13_5) for Key 13
        value_5 = self.findBy('id', 'id_qg_10-0-key_13_1_5')

        # She sees that Key 24 (Remark) is not visible
        key_24 = self.findBy('id', 'id_qg_18-0-original_key_24')
        self.assertFalse(key_24.is_displayed())

        # She selects Value 5 and sees that Key 24 is now visible
        value_5.click()
        self.assertTrue(key_24.is_displayed())

        # She deselects Value 5 and the Key is hidden again
        value_5.click()
        self.assertFalse(key_24.is_displayed())

        # She selects Value 5 and enters some text for Key 24
        value_5.click()
        self.assertTrue(key_24.is_displayed())
        key_24.send_keys('Foo')

        # She selects Value 4 and sees that nothing happens to Key 24
        self.findBy('id', 'id_qg_10-0-key_13_1_4').click()
        self.assertTrue(key_24.is_displayed())
        self.assertEqual(key_24.get_attribute('value'), 'Foo')

        # She deselects Value 5 and selects it again and sees that the
        # entered text is gone.
        value_5.click()
        self.assertFalse(key_24.is_displayed())
        value_5.click()
        self.assertTrue(key_24.is_displayed())
        self.assertEqual(key_24.get_attribute('value'), '')

        # She enters some text again, submits the form and sees that
        # Key 24 was submitted.
        key_24.send_keys('Bar')
        self.submit_form_step()
        self.checkOnPage('Key 13')
        self.checkOnPage('Value 13_5')
        self.checkOnPage('Key 24')
        self.checkOnPage('Bar')

        # She goes back to the form and sees that the values are still
        # there, Key 24 is visible
        self.click_edit_section('cat_2')
        value_5 = self.findBy('id', 'id_qg_10-0-key_13_1_5')
        self.findBy(
            'xpath',
            '//input[@id="id_qg_10-0-key_13_1_5" and @checked="checked"]')
        key_24 = self.findBy('id', 'id_qg_18-0-original_key_24')
        self.assertTrue(key_24.is_displayed())
        self.assertEqual(key_24.get_attribute('value'), 'Bar')

        # She unchecks value 5 and sees that everything is hidden again
        value_5.click()
        self.assertFalse(key_24.is_displayed())

        # She selects Value 5 again and sees it is empty again
        value_5.click()
        self.assertTrue(key_24.is_displayed())
        self.assertEqual(key_24.get_attribute('value'), '')

        # She enters some values again and submits the form completely
        key_24.send_keys('Foo')
        self.submit_form_step()
        self.review_action('submit')

        self.checkOnPage('Key 13')
        self.checkOnPage('Value 13_5')
        self.checkOnPage('Key 24')
        self.checkOnPage('Foo')

    def test_conditional_chaining(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.rearrangeFormHeader()

        # She sees the radio button for Key 11
        key_11_yes = self.findBy('id', 'id_qg_3-0-key_11_1')

        # She does not see the Keys 27 and 28
        key_27_value_3 = self.findBy('id', 'id_qg_22-0-key_27_1_3')
        self.assertFalse(key_27_value_3.is_displayed())
        key_28 = self.findBy('id', 'id_qg_23-0-original_key_28')
        self.assertFalse(key_28.is_displayed())

        # She selects Key 11 and sees that Key 27 is visible but Key 28
        # is not
        key_11_yes.click()
        self.assertTrue(key_27_value_3.is_displayed())
        self.assertFalse(key_28.is_displayed())

        # She selects Key 27 and sees that Key 28 is now visible
        key_27_value_3.click()
        self.assertTrue(key_28.is_displayed())

        # She enters some text for Key 28 and deselects Key 27. She sees
        # that Key 28 is hidden
        key_28.send_keys('Foo')
        key_27_value_3.click()
        self.assertFalse(key_28.is_displayed())

        # She reselects Key 27 and sees Key 28 is visible again but empty
        key_27_value_3.click()
        self.assertTrue(key_28.is_displayed())
        self.assertEqual(key_28.get_attribute('value'), '')

        # She enters some text again and decides to deselect Key 11
        key_28.send_keys('Foo')
        key_11_no = self.findBy('id', 'id_qg_3-0-key_11_2')
        key_11_no.click()

        # She sees that both Key 27 and 28 are not visible anymore
        self.assertFalse(key_27_value_3.is_displayed())
        self.assertFalse(key_28.is_displayed())

        # She reselects Key 11 and sees that only Key 27 is visible and empty
        key_11_yes.click()
        self.assertTrue(key_27_value_3.is_displayed())
        self.assertFalse(key_28.is_displayed())

        # She reselects Key 27 and sees that Key 28 is visible and empty
        key_27_value_3.click()
        self.assertTrue(key_28.is_displayed())
        self.assertEqual(key_28.get_attribute('value'), '')

        # She enters some text and submits the form
        key_28.send_keys('Foo')
        self.submit_form_step()

        # She sees all values were submitted correctly
        self.checkOnPage('Key 11')
        self.checkOnPage('Yes')
        self.checkOnPage('Key 27')
        self.checkOnPage('Value 27 C')
        self.checkOnPage('Key 28')
        self.checkOnPage('Foo')

        # She goes back to the form and sees that the values are still
        # there, Keys 27 and 28 are visible
        self.click_edit_section('cat_1')
        key_11_yes = self.findBy('id', 'id_qg_3-0-key_11_1')
        # She does not see the Keys 27 and 28
        key_27_value_3 = self.findBy(
            'xpath',
            '//input[@id="id_qg_22-0-key_27_1_3" and @checked="checked"]')
        self.assertTrue(key_27_value_3.is_displayed())
        key_28 = self.findBy('id', 'id_qg_23-0-original_key_28')
        self.assertTrue(key_28.is_displayed())
        self.assertEqual(key_28.get_attribute('value'), 'Foo')

        # She submits the form completely and sees all the values were
        # submitted
        self.submit_form_step()
        self.review_action('submit')
        self.checkOnPage('Key 11')
        self.checkOnPage('Yes')
        self.checkOnPage('Key 27')
        self.checkOnPage('Value 27 C')
        self.checkOnPage('Key 28')
        self.checkOnPage('Foo')

    def test_conditional_questions(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))
        self.rearrangeFormHeader()
        cb_1_1 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_16_1"]')
        cb_1_2 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_16_2"]')
        cb_2_1 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_15_1"]')

        # She sees one checkbox, but not the conditional one
        self.assertTrue(cb_1_1.is_displayed())
        self.assertFalse(cb_2_1.is_displayed())

        # She selects a checkbox which triggers the condition, she can now see
        # the conditional question
        cb_1_2.click()
        self.assertTrue(cb_2_1.is_displayed())

        # She deselects the checkbox and selects one which does not trigger
        # anything, she sees the conditional question is hidden again
        cb_1_2.click()
        cb_1_1.click()
        self.assertFalse(cb_2_1.is_displayed())

        # She submits the form step and sees the correct value was submitted
        self.submit_form_step()
        self.findBy('xpath', '//img[@alt="Value 16_1"]')
        self.findByNot('xpath', '//img[@alt="Value 15_1"]')

        # She goes back to the form
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "cat_4"))
        )
        self.click_edit_section('cat_4')
        cb_1_1 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_16_1"]')
        cb_1_2 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_16_2"]')
        cb_2_1 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_15_1"]')

        # She sees the conditional question is not visible
        self.assertFalse(cb_2_1.is_displayed())

        # She deselects the checkbox and selects one with a trigger, the
        # conditional question is visible again
        cb_1_1.click()
        cb_1_2.click()

        # She submits the form and checks the submitted value
        self.submit_form_step()
        self.findBy('xpath', '//img[@alt="Value 16_2"]')
        self.findByNot('xpath', '//img[@alt="Value 15_1"]')

        # She goes back to the form
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "cat_4"))
        )
        self.click_edit_section('cat_4')
        cb_1_1 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_16_1"]')
        cb_1_2 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_16_2"]')
        cb_2_1 = self.findBy('xpath', '//label[@for="id_qg_12-0-key_15_1"]')
        cb_2_1_cb = self.findBy('id', 'id_qg_12-0-key_15_1')

        # She sees the conditional question is visible
        self.assertTrue(cb_2_1.is_displayed())

        # She selects a checkbox of the conditional question
        cb_2_1.click()

        # She deselects the checkbox which triggers and reselects it. She sees
        # the conditional checkbox is not selected anymore
        self.assertEqual(cb_2_1_cb.get_attribute('checked'), 'true')
        cb_1_2.click()
        self.assertFalse(cb_2_1.is_displayed())
        cb_1_2.click()
        self.assertTrue(cb_2_1.is_displayed())
        self.assertIsNone(cb_2_1_cb.get_attribute('checked'))

        # She selects something of the conditional question
        cb_2_1.click()

        # She submits the step
        self.submit_form_step()
        self.findBy('xpath', '//img[@alt="Value 16_2"]')
        self.findBy('xpath', '//img[@alt="Value 15_1"]')

        # She submits the entire form
        self.review_action('submit')
        self.findBy('xpath', '//img[@alt="Value 16_2"]')
        self.findBy('xpath', '//img[@alt="Value 15_1"]')

    # def test_image_checkbox_subcategory(self):

    #     # Alice logs in
    #     self.doLogin()

    #     cat_4_position = get_position_of_category('cat_4')

    #     # She goes to a step of the questionnaire
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_4'}))

    #     # She sees the checkbox images of Key 15 which are not the same
    #     # as for Key 14.
    #     img_1_key_14 = self.findBy('xpath', '//img[@alt="Value 14_1"]')
    #     img_1_key_15 = self.findBy('xpath', '//img[@alt="Value 15_1"]')
    #     self.assertNotEqual(
    #         img_1_key_14.get_attribute('src'),
    #         img_1_key_15.get_attribute('src'))

    #     # She sees that no Checkbox of Key 15 is selected by default
    #     self.findByNot(
    #         'xpath', '//input[@name="qg_12-0-key_15" and @checked="checked"]')

    #     # She also sees that Key 16 is not visible
    #     subcat_val_1 = self.findBy('id', 'id_qg_12-0-key_15_1_sub')
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16"]', base=subcat_val_1)
    #     self.assertIn('display: none;', subcat_val_1.get_attribute('style'))

    #     # She sees that the form progress is at 0
    #     self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

    #     # She submits the form empty and sees that no value was submitted,
    #     # progress of Category 4 is still 0
    #     self.findBy('id', 'button-submit').click()
    #     self.findByNot('xpath', '//*[text()[contains(.,"Key 15")]]')
    #     progress_indicator = self.findBy(
    #         'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
    #             cat_4_position))
    #     self.assertIn('0/', progress_indicator.text)

    #     # She goes back to the questionnaire step and sees that form
    #     # progress is still at 0 and no checkbox is selected
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_4'}))
    #     self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
    #     self.findByNot(
    #         'xpath', '//input[@name="qg_12-0-key_15" and @checked="checked"]')

    #     # She also sees that Key 16 is not visible
    #     subcat_val_1 = self.findBy('id', 'id_qg_12-0-key_15_1_sub')
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16"]', base=subcat_val_1)
    #     self.assertIn('display: none;', subcat_val_1.get_attribute('style'))

    #     # She selects the first checkbox and sees that the form progress
    #     # was updated
    #     self.findBy(
    #         'xpath', '(//input[@name="qg_12-0-key_15"])[1]').click()
    #     self.findBy(
    #         'xpath', '//span[@class="meter" and @style="width: 33.3333%;"]')

    #     # She also sees that Key 16 is now visible but no value is selected
    #     subcat_val_1 = self.findBy('id', 'id_qg_12-0-key_15_1_sub')
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16"]', base=subcat_val_1)
    #     self.browser.implicitly_wait(5)
    #     self.assertNotIn(
    #         'display: none;', subcat_val_1.get_attribute('style')
    #     )
    #     self.findByNot(
    #         'xpath', '//input[@name="qg_12-0-key_16" and @checked="checked"]')

    #     # She submits the step and sees that Key 15 was submitted and
    #     # the form progress on the overview page is updated
    #     self.findBy('id', 'button-submit').click()
    #     self.checkOnPage('Key 15')
    #     self.findBy('xpath', '//img[@alt="Value 15_1"]')
    #     progress_indicator = self.findBy(
    #         'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
    #             cat_4_position))
    #     self.assertIn('1/', progress_indicator.text)

    #     # She goes back to the step and sees that the value of Key 15 is
    #     # selected, form progress is at 1
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_4'}))
    #     self.findBy(
    #         'xpath', '//span[@class="meter" and @style="width: 33.3333%;"]')

    #     # Key 16 is visible but no value selected
    #     subcat_val_1 = self.findBy('id', 'id_qg_12-0-key_15_1_sub')
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16"]', base=subcat_val_1)
    #     self.assertNotIn(
    #         'display: none;', subcat_val_1.get_attribute('style')
    #     )
    #     self.findByNot(
    #         'xpath', '//input[@name="qg_12-0-key_16" and @checked="checked"]')

    #     # She selects a value of Key 16
    #     self.findBy(
    #         'xpath', '(//input[@name="qg_12-0-key_16"])[1]').click()

    #     # She submits the step and sees that both values are submitted
    #     self.findBy('id', 'button-submit').click()
    #     self.checkOnPage('Key 15')
    #     self.findBy('xpath', '//img[@alt="Value 15_1"]')
    #     self.checkOnPage('Key 16')
    #     self.findBy('xpath', '//img[@alt="Value 16_1"]')
    #     progress_indicator = self.findBy(
    #         'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
    #             cat_4_position))
    #     self.assertIn('1/', progress_indicator.text)

    #     # She goes back to the step and sees that the value of Key 15 is
    #     # selected, form progress is at 1
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_4'}))
    #     self.findBy(
    #         'xpath', '//span[@class="meter" and @style="width: 33.3333%;"]')

    #     # She sees that the value of Key 15 is selected. Key 16 is
    #     # visible and the first value is selected.
    #     subcat_val_1 = self.findBy('id', 'id_qg_12-0-key_15_1_sub')
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16"]', base=subcat_val_1)
    #     self.assertNotIn(
    #         'display: none;', subcat_val_1.get_attribute('style'))
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16" and @checked="checked"]')

    #     # She deselects the value of Key 15 and sees that Key 16 is not
    #     # visible anymore
    #     self.findBy(
    #         'xpath', '(//input[@name="qg_12-0-key_15"])[1]').click()

    #     subcat_val_1 = self.findBy('id', 'id_qg_12-0-key_15_1_sub')
    #     self.findBy(
    #         'xpath', '//input[@name="qg_12-0-key_16"]', base=subcat_val_1)
    #     time.sleep(1)
    #     self.assertIn('display: none;', subcat_val_1.get_attribute('style'))

    #     # She reselects the value of Key 15 and sees that the previously
    #     # selected value of Key 16 is not selected anymore.
    #     self.findBy(
    #         'xpath', '(//input[@name="qg_12-0-key_15"])[1]').click()
    #     self.findByNot(
    #         'xpath', '//input[@name="qg_12-0-key_16" and @checked="checked"]')

    #     # She selects two values of Key 16 again and submits the form
    #     self.browser.implicitly_wait(5)
    #     self.findBy(
    #         'xpath', '(//input[@name="qg_12-0-key_16"])[1]').click()
    #     self.findBy(
    #         'xpath', '(//input[@name="qg_12-0-key_16"])[2]').click()
    #     self.findBy('id', 'button-submit').click()
    #     self.checkOnPage('Key 15')
    #     self.findBy('xpath', '//img[@alt="Value 15_1"]')
    #     self.checkOnPage('Key 16')
    #     self.findBy('xpath', '//img[@alt="Value 16_1"]')
    #     self.findBy('xpath', '//img[@alt="Value 16_2"]')

    #     # She submits the form and sees that the values were stored
    #     # correctly
    #     self.findBy('id', 'button-submit').click()
    #     self.checkOnPage('Key 15')
    #     self.findBy('xpath', '//img[@alt="Value 15_1"]')
    #     self.checkOnPage('Key 16')
    #     self.findBy('xpath', '//img[@alt="Value 16_1"]')
    #     self.findBy('xpath', '//img[@alt="Value 16_2"]')

    def test_measure_selects(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))

        # She sees Key 12 in a row which is not selected
        self.findByNot(
            'xpath', '//div[@class="row list-item is-selected"]/div/label['
            'contains(text(), "Key 12")]')

        # She sees that the form progress is at 0
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees that no value was submitted,
        # progress of Category 2 is still 0
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 12")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[3]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and the row is unselected
        self.click_edit_section('cat_2')
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
        self.findByNot(
            'xpath', '//div[contains(@class, "is-selected")]//label/span['
            'text()="low"]')

        # She sees that the values are not ordered alphabetically
        measures = ["low", "medium", "high"]
        for i, m in enumerate(measures):
            self.findBy(
                'xpath', '(//div[@class="button-bar"]/ul/li/label/span)[{}]['
                'contains(text(), "{}")]'.format(i + 1, m))

        # She selects the first value and sees that the row is now
        # selected and the form progress was updated
        self.findBy(
            'xpath', '//label/span[contains(text(), "low")]').click()
        self.findBy(
            'xpath', '//div[contains(@class, "is-selected")]//label/span['
            'text()="low"]')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 25%;"]')

        # She submits the step and sees that the value was submitted and
        # the form progress on the overview page is updated
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[3]/span[@class="steps"]')
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the step and sees the row is highlighted and
        # low selected, form progress is at 1
        self.click_edit_section('cat_2')
        self.findBy(
            'xpath', '//div[contains(@class, "is-selected")]//label/span['
            'text()="low"]')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 25%;"]')

        # She selects None and sees that the row is not highlighted
        # anymore and the progress was updated
        self.findBy(
            'xpath', '//label/span[contains(text(), "low")]').click()
        self.findByNot(
            'xpath', '//div[contains(@class, "is-selected")]//label/span['
            'text()="low"]')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 0%;"]')

        # She then selects medium and submits the form
        self.findBy(
            'xpath', '//label/span[contains(text(), "medium")]').click()
        self.submit_form_step()

        # The overview now shows medium and she submits the form
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')

        # She submits the form and sees that the radio value is stored
        # correctly
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')

    def test_measure_selects_repeating(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
        self.rearrangeFormHeader()

        # She sees Key 12 and selects a measure (low)
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="qg_9"][1]//label/'
            'span[contains(text(), "low")]').click()

        # She adds another questiongroup
        self.findBy(
            'xpath', '//fieldset[@class="row"][2]//a[@data-add-item]').click()

        # She selects measure (medium) in the second
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="qg_9"][2]//label/'
            'span[contains(text(), "medium")]').click()

        # She changes the first measure (high)
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="qg_9"][1]//label/'
            'span[contains(text(), "high")]').click()

        # She submits the step and sees the values were submitted
        # correctly
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"high")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')

        # She goes back to the form and sees the values were populated
        self.click_edit_section('cat_2')
        self.findBy(
            'xpath', '//input[@id="id_qg_9-0-key_12_3" and @checked]')
        self.findBy(
            'xpath', '//input[@id="id_qg_9-1-key_12_2" and @checked]')

        # She changes the values
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="qg_9"][1]//label/'
            'span[contains(text(), "medium")]').click()
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="qg_9"][2]//label/'
            'span[contains(text(), "low")]').click()

        # She submits the step and sees the values were submitted
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')

        # She submits the questionnaire and sees the values were submitted
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')

    def test_date_picker(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.rearrangeFormHeader()

        # She sees that key 47 has a datepicker
        self.findBy(
            'xpath',
            '//input[@name="qg_34-0-key_47" and contains(@class, '
            '"hasDatepicker")]')

        # She sees that the form does not have any progress
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees no value was submitted,
        # progress of Category 1 is still 0
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 11")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[2]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        # She goes to the form again
        self.click_edit_section('cat_1')

        # She does not see the datepicker
        datepicker = self.findBy('id', 'ui-datepicker-div')
        self.assertFalse(datepicker.is_displayed())

        # She sees there is no value in the field
        datefield = self.findBy(
            'xpath',
            '//input[@name="qg_34-0-key_47" and contains(@class, '
            '"hasDatepicker")]')
        self.assertEqual(datefield.get_attribute('value'), '')

        # She clicks the input and sees the datepicker opens
        datefield.click()
        self.assertTrue(datepicker.is_displayed())

        # She selects a date
        self.findBy(
            'xpath',
            '//div[@id="ui-datepicker-div"]/table/tbody/tr[3]/td[4]/a'
        ).click()

        # She sees the value was selected
        selected_date = datefield.get_attribute('value')
        self.assertNotEqual(selected_date, '')

        # She sees that the progress was updated and submits the form.
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.submit_form_step()

        # She sees the value was submitted correctly
        self.findBy('xpath', '//*[text()[contains(.,"{}")]]'.format(
            selected_date))

        # She goes back to the form again and sees the value was correctly
        # populated
        self.click_edit_section('cat_1')
        datefield = self.findBy(
            'xpath',
            '//input[@name="qg_34-0-key_47" and contains(@class, '
            '"hasDatepicker")]')
        self.assertEqual(datefield.get_attribute('value'), selected_date)

        # She clicks "Add more" and selects another date
        self.findBy('xpath', '//a[@data-questiongroup-keyword="qg_34"]').click()

        # She does not see the datepicker
        datepicker = self.findBy('id', 'ui-datepicker-div')
        self.assertFalse(datepicker.is_displayed())

        # She sees there is no value in the field
        datefield_2 = self.findBy(
            'xpath',
            '//input[@name="qg_34-1-key_47" and contains(@class, '
            '"hasDatepicker")]')
        self.assertEqual(datefield_2.get_attribute('value'), '')

        # She clicks the input and sees the datepicker opens
        datefield_2.click()
        self.assertTrue(datepicker.is_displayed())

        # She selects a date
        self.findBy(
            'xpath',
            '//div[@id="ui-datepicker-div"]/table/tbody/tr[3]/td[2]/a'
        ).click()

        # She sees the value was selected
        selected_date_2 = datefield_2.get_attribute('value')
        self.assertNotEqual(selected_date_2, '')

        # She submits the step
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"{}")]]'.format(
            selected_date))
        self.findBy('xpath', '//*[text()[contains(.,"{}")]]'.format(
            selected_date_2))

        # She submits the entire questionnaire
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"{}")]]'.format(
            selected_date))
        self.findBy('xpath', '//*[text()[contains(.,"{}")]]'.format(
            selected_date_2))

    def test_radio_selects(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.rearrangeFormHeader()

        # She sees that Key 11 is a radio button
        radios = self.findManyBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @type="radio"]')
        self.assertEqual(len(radios), 2)

        # She sees that the form does not have any progress
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees no value was submitted,
        # progress of Category 1 is still 0
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 11")]]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[2]/span[@class="steps"]')
        self.assertIn('0/', progress_indicator.text)

        # She goes to the form again and clicks "Yes".
        self.click_edit_section('cat_1')
        self.findBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @value="1"]')\
            .click()

        # She sees that the progress was updated and submits the form.
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.submit_form_step()

        # She sees the value was transmitted and the progress was updated
        self.findBy('xpath', '//*[text()[contains(.,"Key 11")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Yes")]]')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width:50%"]')
        progress_indicator = self.findBy(
            'xpath',
            '(//div[@class="tech-section-progress"])[2]/span[@class="steps"]')
        self.assertIn('1/', progress_indicator.text)

        # She edits the form again and sets the radio button to "No"
        self.click_edit_section('cat_1')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.findBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @value="1" and '
            '@checked=""]')
        self.findBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @value="0"]')\
            .click()
        self.submit_form_step()

        # She sees the value was updated
        self.findBy('xpath', '//*[text()[contains(.,"Key 11")]]')
        self.findBy('xpath', '//*[text()[contains(.,"No")]]')

        # She submits the form and sees the radio value is stored correctly
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 11")]]')
        self.findBy('xpath', '//*[text()[contains(.,"No")]]')

    def test_radio_other(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the Questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.rearrangeFormHeader()

        # She sees there are radio buttons with labels and one with a textfield
        radio_1 = self.findBy('id', 'id_qg_35-0-key_48_1')
        other_radio = self.findBy(
            'xpath', '//label[@for="id_qg_35-0-original_key_49"]/input['
                     'contains(@class, "radio-other")]')
        other_textfield = self.findBy('id', 'id_qg_35-0-original_key_49')

        # She sees the textfield is readonly
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')

        # She selects the radio in front of the textfield and sees she can now
        # edit the textfield, she enters some text.
        other_radio.click()
        self.assertIsNone(other_textfield.get_attribute('readonly'))
        other_textfield.send_keys('foo')

        # She selects another radio and sees the radio in front of the textfield
        # is deselected and the textfield is now empty and readonly
        radio_1.click()
        self.assertIsNone(other_radio.get_attribute('checked'))
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')
        self.assertEqual(other_textfield.get_attribute('value'), '')

        # She submits the step and sees the radio value was submitted
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')

        # She goes back to the form
        self.click_edit_section('cat_1')
        radio_1 = self.findBy('id', 'id_qg_35-0-key_48_1')
        other_radio = self.findBy(
            'xpath', '//label[@for="id_qg_35-0-original_key_49"]/input['
                     'contains(@class, "radio-other")]')
        other_textfield = self.findBy('id', 'id_qg_35-0-original_key_49')

        # She sees the radio was selected, the textfield is readonly
        self.assertEqual(radio_1.get_attribute('checked'), 'true')
        self.assertIsNone(other_radio.get_attribute('checked'))
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')
        self.assertEqual(other_textfield.get_attribute('value'), '')

        # She selects the radio in front of the textfield and enters some text
        other_radio.click()
        other_textfield.send_keys('foo content')

        # She sees that the first radio was deselected
        self.assertIsNone(radio_1.get_attribute('checked'))

        # She submits the step and sees the value was submitted.
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"foo content")]]')

        # She goes back to the form
        self.click_edit_section('cat_1')
        radio_1 = self.findBy('id', 'id_qg_35-0-key_48_1')
        other_radio = self.findBy(
            'xpath', '//label[@for="id_qg_35-0-original_key_49"]/input['
                     'contains(@class, "radio-other")]')
        other_textfield = self.findBy('id', 'id_qg_35-0-original_key_49')

        # She sees the correct radio was selected and she can edit the textfield
        self.assertEqual(other_radio.get_attribute('checked'), 'true')
        self.assertIsNone(radio_1.get_attribute('checked'))
        self.assertIsNone(other_textfield.get_attribute('readonly'))
        self.assertEqual(other_textfield.get_attribute('value'), 'foo content')

        # She deselects the radio and sees the textfield is emptied and readonly
        other_radio.click()
        self.assertIsNone(other_radio.get_attribute('checked'))
        self.assertEqual(other_textfield.get_attribute('readonly'), 'true')
        self.assertEqual(other_textfield.get_attribute('value'), '')

        # She selects the first radio
        radio_1.click()

        # She selects the other radio again
        other_radio.click()

        # And she selects the first radio again
        radio_1.click()

        # She makes sure the first radio is selected
        self.assertEqual(radio_1.get_attribute('checked'), 'true')

        # Once again, she checks the other radio and enters some text
        other_radio.click()
        self.assertEqual(other_radio.get_attribute('checked'), 'true')
        other_textfield.send_keys('foo bar')

        # She submits the step
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"foo bar")]]')

        # She submits the entire questionnaire
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"foo bar")]]')

    def test_plus_questiongroup(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.rearrangeFormHeader()

        # She sees that Subcategory 1_2 contains an additional
        # questiongroups for "plus" questions, the keys initially hidden
        plus_button = self.findBy(
            'xpath', '//ul[contains(@class, "plus-questiongroup")]/li/a')

        key_37 = self.findBy(
            'xpath', '//input[@name="qg_29-0-original_key_37"]')
        key_38 = self.findBy(
            'xpath', '//input[@name="qg_29-0-original_key_38"]')
        self.assertFalse(key_37.is_displayed())
        self.assertFalse(key_38.is_displayed())

        # She clicks on the button and sees the keys are now visible
        plus_button.click()
        self.wait_for('xpath', '//input[@name="qg_29-0-original_key_37"]')
        self.assertTrue(key_37.is_displayed())
        self.assertTrue(key_38.is_displayed())

        # She enters some text and sees that the progress was updated
        key_37.send_keys('Foo')
        key_38.send_keys('Bar')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees that the values were submitted
        # correctly.
        self.submit_form_step()
        self.checkOnPage('Foo')
        self.checkOnPage('Bar')

        # She goes back to the form and sees the additional
        # questiongroups are now visible because they have initial
        # values
        self.click_edit_section('cat_1')

        key_37 = self.findBy(
            'xpath', '//input[@name="qg_29-0-original_key_37"]')
        key_38 = self.findBy(
            'xpath', '//input[@name="qg_29-0-original_key_38"]')
        self.assertTrue(key_37.is_displayed())
        self.assertTrue(key_38.is_displayed())

        # She hides the keys and shows them again, the values are still
        # there
        plus_button = self.findBy(
            'xpath', '//ul[contains(@class, "plus-questiongroup")]/li/a')
        plus_button.click()
        self.wait_for('xpath', '//input[@name="qg_29-0-original_key_37"]',
                      visibility=False)
        self.assertFalse(key_37.is_displayed())
        self.assertFalse(key_38.is_displayed())
        plus_button.click()
        self.wait_for('xpath', '//input[@name="qg_29-0-original_key_37"]')
        self.wait_for('xpath', '//input[@name="qg_29-0-original_key_38"]')

        key_37_value = self.findBy(
            'xpath',
            '//input[@name="qg_29-0-original_key_37" and @value="Foo"]')
        key_38_value = self.findBy(
            'xpath',
            '//input[@name="qg_29-0-original_key_38" and @value="Bar"]')
        self.assertTrue(key_37_value.is_displayed())
        self.assertTrue(key_38_value.is_displayed())

        # She submits the form and sees that the values were submitted
        # correctly.
        self.submit_form_step()
        self.checkOnPage('Foo')
        self.checkOnPage('Bar')

        self.review_action('submit')
        self.checkOnPage('Foo')
        self.checkOnPage('Bar')

    def test_table_entry(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire with a table
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_5'}))
        self.rearrangeFormHeader()

        # She sees a table and enters some values
        table = self.findBy('xpath', '//fieldset[@id="subcat_5_1"]//table')

        headers = self.findManyBy('xpath', '//fieldset[@id="subcat_5_1"]//th')
        self.assertEqual(len(headers), 4)
        self.assertEqual(headers[0].text, 'Key 33')
        self.assertEqual(headers[1].text, 'Key 34')
        self.assertEqual(headers[2].text, 'Key 35')
        self.assertEqual(headers[3].text, 'Key 36')

        row_1 = self.findBy('xpath', '//fieldset[@id="subcat_5_1"]//tr[1]')
        td_1_1 = self.findBy('xpath', '//td[1]', base=row_1)
        self.findBy(
            'xpath', '//input[@name="qg_25-0-original_key_33"]',
            base=td_1_1).send_keys('Foo 1')
        td_1_2 = self.findBy('xpath', '//td[2]', base=row_1)
        self.findBy(
            'xpath', '//input[@name="qg_25-0-original_key_34"]',
            base=td_1_2).send_keys('Bar 1')
        td_1_3 = self.findBy('xpath', '//td[3]', base=row_1)
        td_1_3_row_1 = self.findBy('xpath', '//table/tbody/tr[1]', base=td_1_3)
        self.findBy(
            'xpath', '//input[@name="qg_26-0-original_key_35"]',
            base=td_1_3_row_1).send_keys('Foobar 1_1')
        self.findBy(
            'xpath', '//input[@name="qg_26-0-original_key_36"]',
            base=td_1_3_row_1).send_keys('Foobar 1_2')
        td_1_3_row_2 = self.findBy('xpath', '//table/tbody/tr[2]', base=td_1_3)
        self.findBy(
            'xpath', '//input[@name="qg_26-1-original_key_35"]',
            base=td_1_3_row_2).send_keys('Foobar 2_1')
        self.findBy(
            'xpath', '//input[@name="qg_26-1-original_key_36"]',
            base=td_1_3_row_2).send_keys('Foobar 2_2')

        row_2 = self.findBy('xpath', '//tr[2]', base=table)
        td_2_1 = self.findBy('xpath', '//td[1]', base=row_2)
        self.findBy(
            'xpath', '//input[@name="qg_27-0-original_key_33"]',
            base=td_2_1).send_keys('Foo 2')
        td_2_2 = self.findBy('xpath', '//td[2]', base=row_2)
        self.findBy(
            'xpath', '//input[@name="qg_27-0-original_key_34"]',
            base=td_2_2).send_keys('Bar 2')
        td_2_3 = self.findBy('xpath', '//td[3]', base=row_2)
        td_2_3_row_1 = self.findBy('xpath', '//table/tbody/tr[1]', base=td_2_3)
        self.findBy(
            'xpath', '//input[@name="qg_28-0-original_key_35"]',
            base=td_2_3_row_1).send_keys('Foobar 3_1')
        self.findBy(
            'xpath', '//input[@name="qg_28-0-original_key_36"]',
            base=td_2_3_row_1).send_keys('Foobar 3_2')

        self.submit_form_step()
        self.wait_for('xpath', '//td[contains(text(), "Foobar 3_2")]')

        # She sees that the values are represented as table
        table = self.findBy('xpath', '//div/table')
        table_text = table.text

        headers = self.findManyBy('xpath', '//th', base=table)
        self.assertEqual(len(headers), 4)
        self.assertEqual(headers[0].text, 'Key 33')
        self.assertEqual(headers[1].text, 'Key 34')
        self.assertEqual(headers[2].text, 'Key 35')
        self.assertEqual(headers[3].text, 'Key 36')

        row_1 = self.findBy('xpath', '//tr[1]', base=table)
        td_1_1 = self.findBy('xpath', '//td[1]', base=row_1)
        self.assertEqual(td_1_1.text, 'Foo 1')
        td_1_2 = self.findBy('xpath', '//td[2]', base=row_1)
        self.assertEqual(td_1_2.text, 'Bar 1')
        td_1_3_1_1 = self.findBy(
            'xpath', '//table/tbody/tr[1]/td[3]/table/tbody/tr[1]/td[1]')
        self.assertEqual(td_1_3_1_1.text, 'Foobar 1_1')
        td_1_3_1_2 = self.findBy(
            'xpath', '//table/tbody/tr[1]/td[3]/table/tbody/tr[1]/td[2]')
        self.assertEqual(td_1_3_1_2.text, 'Foobar 1_2')
        td_1_3_2_1 = self.findBy(
            'xpath', '//table/tbody/tr[1]/td[3]/table/tbody/tr[2]/td[1]')
        self.assertEqual(td_1_3_2_1.text, 'Foobar 2_1')
        td_1_3_2_2 = self.findBy(
            'xpath', '//table/tbody/tr[1]/td[3]/table/tbody/tr[2]/td[2]')
        self.assertEqual(td_1_3_2_2.text, 'Foobar 2_2')

        td_2_1 = self.findBy('xpath', '//div/table/tbody/tr[2]/td[1]')
        self.assertEqual(td_2_1.text, 'Foo 2')
        td_2_2 = self.findBy('xpath', '//div/table/tbody/tr[2]/td[2]')
        self.assertEqual(td_2_2.text, 'Bar 2')
        td_2_3_1_1 = self.findBy(
            'xpath', '//table/tbody/tr[2]/td[3]/table/tbody/tr[1]/td[1]')
        self.assertEqual(td_2_3_1_1.text, 'Foobar 3_1')
        td_2_3_1_2 = self.findBy(
            'xpath', '//table/tbody/tr[2]/td[3]/table/tbody/tr[1]/td[2]')
        self.assertEqual(td_2_3_1_2.text, 'Foobar 3_2')

        self.review_action('submit')
        self.wait_for('xpath', '//td[contains(text(), "Foobar 3_2")]')

        table_output = self.findBy('xpath', '//div/table')
        self.assertEqual(table_text, table_output.text)

    # def test_enter_questionnaire_requires_login(self):

    #     # Alice opens the login form and does not see a message
    #     self.browser.get(self.live_server_url + reverse(accounts_route_login))
    #     self.findByNot(
    #         'xpath', '//div[@class="alert-box info" and contains(text(), "' +
    #         reverse(route_questionnaire_new) + '")]')

    #     # Alice tries to access the form without being logged in
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new))
    #     self.findBy(
    #         'xpath', '//div[@class="alert-box info" and contains(text(), "' +
    #         reverse(route_questionnaire_new) + '")]')

    #     # She sees that she has been redirected to the login page
    #     self.checkOnPage('Login')
    #     # self.checkOnPage(reverse(
    #     #     route_questionnaire_new))
    #     self.findBy('name', 'user').send_keys('a@b.com')
    #     self.findBy('name', 'pass').send_keys('foo')
    #     self.findBy('id', 'button_login').click()

    #     # She sees that she is logged in and was redirected back to the form.
    #     # self.checkOnPage('Category 1')

    def test_header_image(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))
        self.rearrangeFormHeader()

        # She sees a field to put files, drawn by Dropzone
        dropzone = self.findBy(
            'xpath', '//div[@id="id_qg_14-0-file_key_19" and contains(@class, '
            '"dropzone")]')
        self.assertTrue(dropzone.is_displayed())

        # She does not see the preview field, which is hidden and does not
        # contain an image
        preview = self.findBy(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]')
        self.assertFalse(preview.is_displayed())
        self.findByNot(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]/'
            'div[@class="image-preview"]/img')

        # The hidden input field is empty
        filename = self.findBy('xpath', '//input[@id="id_qg_14-0-key_19"]')
        self.assertEqual(filename.get_attribute('value'), '')

        # She sees that the form does not have any progress
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She uploads an image
        self.dropImage('id_qg_14-0-file_key_19')

        # She sees that the dropzone is hidden, the preview is visible
        self.assertFalse(dropzone.is_displayed())
        self.assertTrue(preview.is_displayed())

        # Preview contains an image
        self.findBy(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]/'
            'div[@class="image-preview"]/img')

        # The filename was added to the hidden input field
        self.assertNotEqual(filename.get_attribute('value'), '')

        # She sees that the progress was updated.
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She removes the file
        self.findBy(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]/div/button'
        ).click()

        # She sees the image was removed and the preview container is not
        # visible anymore
        self.findByNot(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]/'
            'div[@class="image-preview"]/img')
        self.assertFalse(preview.is_displayed())

        # She sees the dropzone container again
        self.assertTrue(dropzone.is_displayed())

        # The hidden input field is empty again
        self.assertEqual(filename.get_attribute('value'), '')

        # She sees that the form does not have any progress
        self.findBy('xpath', '//span[@class="meter" and @style="width: 0%;"]')

        # She uploads an image again
        self.dropImage('id_qg_14-0-file_key_19')

        # Dropzone is hidden, preview is there, filename was written to field
        self.assertFalse(dropzone.is_displayed())
        self.assertTrue(preview.is_displayed())
        self.assertNotEqual(filename.get_attribute('value'), '')

        # She sees that the progress was updated.
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form
        self.submit_form_step()

        # On the overview page, she sees the image she uploaded
        self.findBy('xpath',
                    '//div[contains(@class, "file-preview-container")]//img')

        # She edits the form again and sees the image was populated correctly.
        self.click_edit_section('cat_0')

        # Dropzone is hidden, preview is there, filename was written to field
        dropzone = self.findBy(
            'xpath', '//div[@id="id_qg_14-0-file_key_19" and contains(@class, '
            '"dropzone")]')
        self.wait_for('xpath', '//div[@id="id_qg_14-0-file_key_19" and contains(@class, '
            '"dropzone")]', visibility=False)
        self.assertFalse(dropzone.is_displayed())
        preview = self.findBy(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]')
        self.assertTrue(preview.is_displayed())
        filename = self.findBy('xpath', '//input[@id="id_qg_14-0-key_19"]')
        self.assertNotEqual(filename.get_attribute('value'), '')

        # She submits the form and sees that the image was submitted correctly.
        self.submit_form_step()
        self.findBy('xpath',
                    '//div[contains(@class, "file-preview-container")]//img')

        self.review_action('submit')


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch('questionnaire.views.generic_questionnaire_list')
class QuestionnaireTestIndex(FunctionalTest):
    # Tests requiring an index

    fixtures = [
        'sample_global_key_values.json', 'sample.json', 'samplemulti.json',
        'sample_samplemulti_questionnaires.json']

    def setUp(self):
        super(QuestionnaireTestIndex, self).setUp()
        delete_all_indices()
        create_temp_indices(['sample', 'samplemulti'])

    def tearDown(self):
        super(QuestionnaireTestIndex, self).tearDown()
        delete_all_indices()

    @patch.object(WocatAuthenticationMiddleware, 'process_request')
    def test_enter_questionnaire(self, mock_questionnaire_list,
                                 mock_process_request):
        mock_process_request.return_value = {}
        mock_questionnaire_list.return_value = {}
        # Alice logs in
        self.doLogin()

        # She goes directly to the Sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))

        # She sees the categories but without content, keys and
        # subcategories are hidden if they are empty.
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_1")]')
        self.findByNot(
            'xpath', '//article//article//*[contains(text(), "Key 1")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Bar")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_2")]')
        self.findByNot(
            'xpath', '//article//*[text()[contains(.,"Key 4")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 2_1")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 5")]]')

        # She sees the author is not filled out
        self.findByNot(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/a['
            'contains(text(), "bar foo")]')

        # She sees X buttons to edit a category and clicks the first
        edit_buttons = self.findManyBy(
            'xpath',
            '//div[contains(@class, "tech-section-action")]/a')
        self.assertEqual(len(edit_buttons), get_category_count())
        self.click_edit_section('cat_1')

        # She sees the form for Category 1
        self.findBy('xpath', '//h2[contains(text(), "Category 1")]')
        self.findBy('xpath', '//legend[contains(text(), "Subcategory 1_1")]')
        self.findBy('xpath', '//legend[contains(text(), "Subcategory 1_2")]')

        # She enters Key 1
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')

        # # She tries to submit the form and sees an error message saying
        # # that Key 3 is also required.
        # self.findBy('id', 'button-submit').click()
        # error = self.findBy(
        #     'xpath', '//div[contains(@class, "qg_1")]/ul[contains(@class, '
        #     '"errorlist")]/li')
        # self.assertEqual(error.text, "This field is required.")

        # She enters Key 3 and submits the form again
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.submit_form_step()

        # She sees that she was redirected to the overview page and is
        # shown a success message
        self.findBy(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_1")]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Key 1")]]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Bar")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_2")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 4")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 2_1")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 5")]]')

        # She sees the author is already filled out
        self.findBy(
            'xpath', '//ul[contains(@class, "tech-infos")]/li/a['
            'contains(text(), "bar foo")]')

        # She submits the entire questionnaire
        self.review_action('submit')

        # She is being redirected to the details page and sees a success
        # message.
        self.findBy(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_1")]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Key 1")]]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Bar")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_2")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 4")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 2_1")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 5")]]')

        # She sees the author is still filled out
        self.findBy(
            'xpath', '//ul[contains(@class, "tech-infos")]/li/a['
            'contains(text(), "bar foo")]')

        # She sees that the # was removed from the URL
        self.assertIn('#top', self.browser.current_url)

        # She sees that on the detail page, there is no edit button as the
        # questionnaire is in review
        self.findByNot('xpath', '//a[contains(text(), "Edit")]')

        # She goes to the list of questionnaires and sees that the
        #  questionnaire she created is listed there.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list))
        self.checkOnPage('All')
        self.checkOnPage('Foo')

        # If she goes to the questionnaire overview form again, she sees
        # that the session values are not there anymore.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_1")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 1")]]')
        self.findByNot('xpath', '//article//*[contains(text(), "Foo")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Bar")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 1_2")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 4")]]')
        self.findByNot(
            'xpath', '//article//h3[contains(text(), "Subcategory 2_1")]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 5")]]')


class QuestionnaireLinkTest(FunctionalTest):

    fixtures = [
        'sample_global_key_values.json', 'sample.json', 'samplemulti.json',
        'sample_samplemulti_questionnaires.json']

    @patch.object(WocatAuthenticationMiddleware, 'process_request')
    def test_add_questionnaire_link(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a part of the questionnaire and enters some data
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')

        # She submits the step
        self.submit_form_step()

        # She goes to the part where she can edit linked questionnaires
        self.rearrange_notifications()
        self.click_edit_section('cat_5')

        # She sees there is a hidden field for the ID but it is empty
        id_field = self.findBy('name', 'qg_33__samplemulti-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '')

        # She sees a field to search for linked questionnaires
        self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]'
            '[1]').send_keys('key')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is key 1b"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is key 1a"'
            ']').click()
        # She sees that a field with the name was added
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is key 1a")]')

        # She sees the ID was added to the hidden field
        id_field = self.findBy('name', 'qg_33__samplemulti-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '3')

        # She removes the link and sees the box is gone and the ID field is
        # empty
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()
        self.findByNot(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is key 1a")]')
        id_field = self.findBy('name', 'qg_33__samplemulti-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '')

        # She adds the link again
        self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]'
            '[1]').send_keys('key')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is key 1a"'
            ']').click()

        # She submits the step
        self.submit_form_step()

        # She sees that the link was added in category 6
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1a")]]')

        # She goes back to the form and sees the one she linked is still
        # in the form.
        self.rearrange_notifications()
        self.click_edit_section('cat_5')
        id_field = self.findBy('name', 'qg_33__samplemulti-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '3')
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is key 1a")]')

        # She deletes the link and submits the form
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()
        id_field = self.findBy('name', 'qg_33__samplemulti-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '')

        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"This is key 1a")]]')

        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "cat_5"))
        )
        # She links another questionnaire
        self.click_edit_section('cat_5')
        self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]'
            '[1]').send_keys('key')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is key 1b"]').\
            click()

        # She submits the step
        self.submit_form_step()

        # She sees that the link was added in category 6
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1b")]]')

        # She submits the complete form
        self.review_action('submit')

        # She sees that the link was added in category 6
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1b")]]')

        # The link can be clicked
        self.wait_for('xpath', '//a[contains(@href, "samplemulti/view/")]')
        self.findBy(
            'xpath', '//a[contains(@href, "samplemulti/view/")]').click()
        self.checkOnPage('MSection')

        # There is a link back
        self.findBy('xpath', '//a[contains(@href, "sample/view/")]')

    @patch.object(WocatAuthenticationMiddleware, 'process_request')
    def test_edit_questionnaire_link(self, mock_process_request):
        mock_process_request.return_value = None
        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She opens an existing questionnaire and sees the link
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, args=['sample_1']))
        self.toggle_all_sections()

        self.findBy('xpath', '//*[text()[contains(.,"This is key 1a")]]')
        self.wait_for('xpath', '//figure[contains(@class, "tech-thumbnail")]')
        self.findBy(
            'xpath',
            '//figure[contains(@class, "tech-thumbnail")]/a[contains(@href, '
            '"samplemulti/view/")]').click()

        self.toggle_all_sections()
        self.wait_for('xpath', '//figure[contains(@class, "tech-thumbnail")]')
        self.findBy(
            'xpath', '//figure[contains(@class, "tech-thumbnail")]/a[contains('
                     '@href, "sample/view/")]').click()

        # She decides to edit the questionnaire
        self.review_action('edit')

        # She sees the link in the edit overview
        self.findBy(
            'xpath', '//*[text()[contains(.,"Subcategory 5_3 (links)")]]')
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1a")]]')

        # She edits the link form and sees the values are populated correctly
        self.click_edit_section('cat_5')

        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is key 1a")]')
        id_field = self.findBy('name', 'qg_33__samplemulti-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '3')

        # She deletes the link and submits the entire form
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()

        self.submit_form_step()
        self.findByNot(
            'xpath', '//*[text()[contains(.,"Subcategory 5_3 (links)")]]')

        self.review_action('submit')

        self.findByNot(
            'xpath', '//*[text()[contains(.,"Subcategory 5_3 (links)")]]')

    @patch.object(WocatAuthenticationMiddleware, 'process_request')
    def test_edit_questionnaire_multiple_links(self, mock_process_request):
        mock_process_request.return_value = None

        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She opens an existing questionnaire (samplemulti) and sees the link
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details_samplemulti, args=['samplemulti_1']))

        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')

        # She decides to edit the questionnaire
        self.review_action('edit')

        # She sees the link in the edit overview
        self.findBy(
            'xpath', '//*[text()[contains(.,"MSubcategory 1_2 (links)")]]')
        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')

        # She decides to edit the link and sees that the field is
        # populated correctly
        self.click_edit_section('mcat_1')
        self.rearrangeFormHeader()
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is the first key")]')
        id_field = self.findBy('name', 'mqg_02__sample-0-link_id')
        self.assertEqual(id_field.get_attribute('value'), '1')

        # She clicks the button to add another link
        self.findBy('xpath', '//a[@data-questiongroup-keyword="mqg_02__sample" '
                             'and @data-add-item]').click()

        # She tries to add the same link again, this does not work.
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="mqg_02__sample"][2]//'
                     'input[contains(@class, "link-search-field")]'
        ).send_keys('key')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is the first '
            'key."]').click()
        x = self.findManyBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            ' "This is the first key")]')
        self.assertEqual(len(x), 1)

        # She adds another link
        self.findBy(
            'xpath', '//div[@data-questiongroup-keyword="mqg_02__sample"][2]//'
                     'input[contains(@class, "link-search-field")]'
        ).send_keys('foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"]').\
            click()

        # She submits the step
        self.submit_form_step()

        # She sees that both links were added
        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')

        # She submits the form and sees that both links were correctly
        # submitted.
        self.review_action('submit')
        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')

    @patch('samplemulti.views.generic_questionnaire_link_search')
    def test_search(self, mock_link_search):

        # Alice logs in
        self.doLogin()

        # She goes to the section containing the links of a new questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_5'}))
        self.rearrangeFormHeader()

        search_field = self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")][1]')

        mock_link_search.return_value = JsonResponse({
            'total': 0,
            'data': []
        })
        search_field.send_keys('foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        # She enters the name of link which does not exist. She gets a
        # notice and when she clicks it, no link is added.
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="No results found"]'
        ).click()
        self.findByNot(
            'xpath',
            '//div[contains(@class, "alert-box")]')

        search_field.clear()
        # She enters something which returns more results than expected
        data = [{
            'name': 'foo',
            'code': 'bar',
            'display': 'foo',
            'value': 1,
        }] * 15
        mock_link_search.return_value = JsonResponse({
            'total': 15,
            'data': data
        })

        search_field.send_keys('foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        # She gets a message saying there are too many results to
        # display them all. Clicking on the message does not do
        # anything. Not all results are shown.
        results = self.findManyBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="foo"]')
        self.assertEqual(len(results), 10)
        # self.rearrangeFormHeader()
        # self.findBy(
        #     'xpath',
        #     '//li[@class="ui-menu-item"]//strong[contains(text(), "Too many '
        #     'results")]'
        # ).click()
        # self.findByNot(
        #     'xpath',
        #     '//div[contains(@class, "alert-box")]')
        #
        # # The search field is still visible
        # search_field = self.findBy(
        #     'xpath', '//input[contains(@class, "link-search-field")][1]')

    """
    Test:
    * Show pending
    """


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class QuestionnaireTestProjects(FunctionalTest):

    fixtures = ['global_key_values.json', 'sample.json',
                'sample_projects.json', 'sample_institutions.json']

    @patch.object(WocatAuthenticationMiddleware, 'process_request')
    def test_select_project(self, mock_process_request):

        mock_process_request.return_value = None

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
        self.rearrangeFormHeader()

        # She sees Key 52, which is a select field rendered with Chosen
        self.findBy('xpath', '//select[@name="qg_37-0-key_52"]')
        chosen_field = self.findBy('xpath', '//a[@class="chosen-single"]')
        self.assertEqual(chosen_field.text, '-')

        # She sees that the values are ordered alphabetically and the list only
        # shows active projects
        values = ['International Project for Collecting Technologies (IPCT)',
                  'The first Project (TFP)']
        for i, v in enumerate(values):
            self.findBy(
                'xpath',
                '//select[@name="qg_37-0-key_52"]/option[{}][contains(text(),'
                ' "{}")]'.format(i + 2, v))

        # She selects a project
        self.findBy(
            'xpath', '//div[contains(@class, "chosen-container")]').click()
        self.findBy(
            'xpath', '//ul[@class="chosen-results"]/li[contains(text(), '
                     '"International")]').click()
        self.assertEqual(chosen_field.text, 'International Project for '
                                            'Collecting Technologies (IPCT)')

        # She submits the step
        self.submit_form_step()

        # She sees that the display value is visible in the overview (as Key 53)
        self.findBy('xpath', '//*[text()[contains(.,"Key 53")]]')
        self.findBy('xpath', '//*[text()[contains(.,"International Project for '
                             'Collecting Technologies")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 52")]]')

        # She goes back to the step and deselects the project
        self.click_edit_section('cat_2')
        self.findBy(
            'xpath', '//div[contains(@class, "chosen-container")]').click()
        self.findBy(
            'xpath',
            '//ul[@class="chosen-results"]/li[contains(text(), "-")]').click()

        # She submits the step and sees the project is gone in the overview
        self.submit_form_step()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 53")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 52")]]')

        # She goes back to the step and selects another project
        self.click_edit_section('cat_2')
        self.findBy(
            'xpath', '//div[contains(@class, "chosen-container")]').click()
        self.findBy(
            'xpath',
            '//ul[@class="chosen-results"]/li[contains(text(), "first")]').\
            click()

        # She sees that she can also select an institution, which she does
        self.findBy(
            'xpath', '(//div[contains(@class, "chosen-container")])[2]').click()
        self.findBy(
            'xpath',
            '//ul[@class="chosen-results"]/li[contains(text(), "Global")]'). \
            click()

        # She submits the step
        self.submit_form_step()
        self.findBy('xpath', '//*[text()[contains(.,"Key 53")]]')
        self.findBy('xpath',
                    '//*[text()[contains(.,"The first Project (TFP)")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 52")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 55")]]')
        self.findBy('xpath',
                    '//*[text()[contains(.,"Global Institution")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 54")]]')

        # She submits the questionnaire and sees the project is submitted
        self.review_action('submit')
        self.findBy('xpath', '//*[text()[contains(.,"Key 53")]]')
        self.findBy('xpath',
                    '//*[text()[contains(.,"The first Project (TFP)")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 52")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 55")]]')
        self.findBy('xpath',
                    '//*[text()[contains(.,"Global Institution")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 54")]]')
