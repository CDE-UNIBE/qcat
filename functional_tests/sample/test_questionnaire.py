import time
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.test.utils import override_settings
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from unittest.mock import patch

from accounts.client import Typo3Client
from accounts.models import User
from functional_tests.base import FunctionalTest
from questionnaire.models import File
from sample.tests.test_views import (
    route_questionnaire_details,
    route_questionnaire_link_form,
    route_questionnaire_list,
    route_questionnaire_new,
    route_questionnaire_new_step,
    get_category_count,
    get_position_of_category,
)
from samplemulti.tests.test_views import route_questionnaire_details as \
    route_questionnaire_details_samplemulti
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices

from nose.plugins.attrib import attr  # noqa
# @attr('foo')

TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class QuestionnaireTest(FunctionalTest):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def test_translation(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to the form and sees the categories in English
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        self.checkOnPage('English')
        self.findBy('xpath', '//h2[contains(text(), "Category 1")]')

        # She sees the categories do not have any progress
        self.findBy(
            'xpath', '//div[@class="tech-section-progress progress"]/'
            'span[@class="meter" and @style="width:0%"]')

        # She changes the language to Spanish and sees the translated
        # categories
        self.changeLanguage('es')
        self.checkOnPage('Inglés')
        self.findBy('xpath', '//h2[contains(text(), "Categoría 1")]')

        # She changes the language to French and sees there is no
        # translation but the original English categories are displayed
        self.changeLanguage('fr')
        self.checkOnPage('Anglais')
        self.findBy('xpath', '//h2[contains(text(), "Category 1")]')

    def test_navigate_questionnaire(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        # She sees that the first question is active, the second not
        self.findBy(
            'xpath',
            '//a[@data-magellan-destination="question1" and @class="active"]')
        self.findByNot(
            'xpath',
            '//a[@data-magellan-destination="question2" and @class="active"]')

        # She clicks the button to go to the next question
        self.findBy('xpath', '//a[@data-magellan-step="next"]').click()
        self.browser.implicitly_wait(5)

        # Now the first question is inactive, the second is active
        self.findBy(
            'xpath',
            '//a[@data-magellan-destination="question2" and @class="active"]')
        self.findByNot(
            'xpath',
            '//a[@data-magellan-destination="question1" and @class="active"]')

        # A click on the other button goes up one question
        self.findBy('xpath', '//a[@data-magellan-step="previous"]').click()
        self.browser.implicitly_wait(5)
        self.findBy(
            'xpath',
            '//a[@data-magellan-destination="question1" and @class="active"]')
        self.findByNot(
            'xpath',
            '//a[@data-magellan-destination="question2" and @class="active"]')

    def test_numbered_questiongroups(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))

        # She sees that the Questiongroup with Key 9 is numbered
        fieldset = self.findBy('xpath', '//fieldset[@class="row"][2]')

        numbered_1 = self.findBy(
            'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
            ')])[1]', base=fieldset)
        self.assertEqual(numbered_1.text, '1:')
        numbered_2 = self.findBy(
            'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
            ')])[2]', base=fieldset)
        self.assertEqual(numbered_2.text, '2:')

        # She enters some data for the Keys 9
        self.findBy('id', 'id_qg_7-0-original_key_9').send_keys(
            'This is the first key')
        self.findBy('id', 'id_qg_7-1-original_key_9').send_keys('Second key')

        # She submits the step and sees the values are presented in the
        # correct order in the overview
        self.findBy('id', 'button-submit').click()
        res = self.findManyBy(
            'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')

        self.assertEqual(len(res), 2)
        self.assertIn('This is the first key', res[0].text)
        self.assertIn('Second key', res[1].text)

        # She starts editing again and sees that the keys are displayed
        # in the correct order
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))
        self.findBy(
            'xpath', '//input[@id="id_qg_7-0-original_key_9" and @value="This '
            'is the first key"]')
        self.findBy(
            'xpath', '//input[@id="id_qg_7-1-original_key_9" and @value="'
            'Second key"]')

        fieldset = self.findBy('xpath', '//fieldset[@class="row"][2]')

        # She changes the order of the keys by drag-and-drop
        el_1 = self.findBy(
            'xpath', '//fieldset[@class="row"][2]//p[contains(@class, '
            '"questiongroup-numbered-number")][1]',
            base=fieldset)
        ActionChains(self.browser).click_and_hold(
            on_element=el_1).move_by_offset(0, 100).release().perform()

        # She submits the step and sees the values are presented in the
        # correct order in the overview
        self.findBy('id', 'button-submit').click()

        res = self.findManyBy(
            'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
        self.assertEqual(len(res), 2)
        self.assertIn('Second key', res[0].text)
        self.assertIn('This is the first key', res[1].text)

        # She goes back to the form and sees the order persists
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))
        self.findBy(
            'xpath', '//input[@id="id_qg_7-0-original_key_9" and @value="'
            'Second key"]')
        self.findBy(
            'xpath', '//input[@id="id_qg_7-1-original_key_9" and @value="'
            'This is the first key"]')

        # She submits the step and the entire questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('id', 'button-submit').click()

        # She sees that the values were submitted correctly
        self.findBy('xpath', '//div[contains(@class, "success")]')
        res = self.findManyBy(
            'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
        self.assertEqual(len(res), 2)
        self.assertIn('Second key', res[0].text)
        self.assertIn('This is the first key', res[1].text)

    def test_numbered_questiongroups_2(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))

        # She sees that the Questiongroup with Keys 17 and 18 is numbered
        fieldset = self.findBy('xpath', '//fieldset[@class="row"][1]')

        numbered_1 = self.findBy(
            'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
            ')])[1]', base=fieldset)
        self.assertEqual(numbered_1.text, '1:')
        numbered_2 = self.findBy(
            'xpath', '(//p[contains(@class, "questiongroup-numbered-number"'
            ')])[2]', base=fieldset)
        self.assertEqual(numbered_2.text, '2:')

        # She enters some data for the Keys 17 and 18
        self.findBy('id', 'id_qg_13-0-original_key_17').send_keys('Key 17 - 1')
        self.findBy('id', 'id_qg_13-0-original_key_18').send_keys('Key 18 - 1')
        self.findBy('id', 'id_qg_13-1-original_key_17').send_keys('Key 17 - 2')
        self.findBy('id', 'id_qg_13-1-original_key_18').send_keys('Key 18 - 2')

        # She submits the step and sees the values are presented in the
        # correct order in the overview
        self.findBy('id', 'button-submit').click()
        res = self.findManyBy(
            'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
        self.assertEqual(len(res), 2)
        self.assertIn('Key 17 - 1', res[0].text)
        self.assertIn('Key 18 - 1', res[0].text)
        self.assertIn('Key 17 - 2', res[1].text)
        self.assertIn('Key 18 - 2', res[1].text)

        # She starts editing again and sees that the keys are displayed
        # in the correct order
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))
        self.findBy(
            'xpath', '//input[@id="id_qg_13-0-original_key_17" and '
            '@value="Key 17 - 1"]')
        self.findBy(
            'xpath', '//textarea[@id="id_qg_13-0-original_key_18" and '
            'text()="Key 18 - 1"]')
        self.findBy(
            'xpath', '//input[@id="id_qg_13-1-original_key_17" and '
            '@value="Key 17 - 2"]')
        self.findBy(
            'xpath', '//textarea[@id="id_qg_13-1-original_key_18" and '
            'text()="Key 18 - 2"]')

        self.findByNot(
            'xpath', '//input[@id="id_qg_13-2-original_key_17"]')

        # She adds another questiongroup
        self.findBy(
            'xpath', '//fieldset[@class="row"][1]//div[contains(@class, '
            '"questiongroup")][3]//a[contains(text(), "Add More")]').click()

        # The new questiongroup has the number 3:
        fieldset = self.findBy('xpath', '//fieldset[@class="row"][1]')
        numbered_3 = self.findBy(
            'xpath', '//fieldset[@class="row"][1]//div[contains(@class, '
            '"questiongroup")][3]/div[contains(@class, "row")][3]//p['
            'contains(@class, "questiongroup-numbered-number")]')
        self.assertEqual(numbered_3.text, '3:')

        # She adds some content to the 3rd questiongroup
        self.findBy('id', 'id_qg_13-2-original_key_17').send_keys('Key 17 - 3')
        self.findBy('id', 'id_qg_13-2-original_key_18').send_keys('Key 18 - 3')

        # She also decides to change the order
        el_1 = self.findBy(
            'xpath', '//fieldset[@class="row"][1]/div[contains(@class, '
            '"questiongroup")][3]/div[contains(@class, "row")][2]//p['
            'contains(@class, "questiongroup-numbered-number")]')
        ActionChains(self.browser).click_and_hold(
            on_element=el_1).move_by_offset(0, -200).release().perform()

        # She submits the step and sees the values are presented in the
        # correct order in the overview
        self.findBy('id', 'button-submit').click()
        res = self.findManyBy(
            'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
        self.assertEqual(len(res), 3)
        self.assertIn('Key 17 - 2', res[0].text)
        self.assertIn('Key 18 - 2', res[0].text)
        self.assertIn('Key 17 - 1', res[1].text)
        self.assertIn('Key 18 - 1', res[1].text)
        self.assertIn('Key 17 - 3', res[2].text)
        self.assertIn('Key 18 - 3', res[2].text)

        # She goes back to the form and sees the order persists
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))

        self.findBy(
            'xpath', '//input[@id="id_qg_13-0-original_key_17" and '
            '@value="Key 17 - 2"]')
        self.findBy(
            'xpath', '//textarea[@id="id_qg_13-0-original_key_18" and '
            'text()="Key 18 - 2"]')
        self.findBy(
            'xpath', '//input[@id="id_qg_13-1-original_key_17" and '
            '@value="Key 17 - 1"]')
        self.findBy(
            'xpath', '//textarea[@id="id_qg_13-1-original_key_18" and '
            'text()="Key 18 - 1"]')
        self.findBy(
            'xpath', '//input[@id="id_qg_13-2-original_key_17" and '
            '@value="Key 17 - 3"]')
        self.findBy(
            'xpath', '//textarea[@id="id_qg_13-2-original_key_18" and '
            'text()="Key 18 - 3"]')

        # She submits the step and the entire questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('id', 'button-submit').click()

        # She sees that the values were submitted correctly
        self.findBy('xpath', '//div[contains(@class, "success")]')
        res = self.findManyBy(
            'xpath', '//div[contains(@class, "questiongroup-numbered-right")]')
        self.assertEqual(len(res), 3)
        self.assertIn('Key 17 - 2', res[0].text)
        self.assertIn('Key 18 - 2', res[0].text)
        self.assertIn('Key 17 - 1', res[1].text)
        self.assertIn('Key 18 - 1', res[1].text)
        self.assertIn('Key 17 - 3', res[2].text)
        self.assertIn('Key 18 - 3', res[2].text)

    def test_repeating_questiongroups(self, mock_get_user_id):

        initial_button_count = 4

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))

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

        # The butto to add another one is not visible anymore
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
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))

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
        self.findBy('id', 'button-submit').click()

    def test_form_progress(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()
        cat_1_position = get_position_of_category('cat_1')

        # She goes directly to the Sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))

        # She sees that all progress bars are to 0%
        progress_indicators = self.findManyBy(
            'xpath', '//div[@class="tech-section-progress progress"]')
        self.assertEqual(len(progress_indicators), get_category_count())
        buttons = self.findManyBy(
            'xpath', '//a[contains(@href, "edit/new/cat")]')
        for x in buttons:
            self.assertIn('0/', x.text)
        progress_bars = self.findManyBy(
            'xpath', '//span[@class="meter" and @style="width:0%"]')
        self.assertEqual(len(progress_bars), len(progress_indicators))

        # She goes to the first category and sees another progress bar
        self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position)).click()
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
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position))
        self.assertIn('1/2', progress_indicator.text)

        # She decides to edit the step again and deletes what she
        # entered. She notices that the bar is back to 0, also on the
        # overview page.
        self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position)).click()
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 0%;"]')
        self.findBy('id', 'button-submit').click()

        progress_indicators = self.findManyBy(
            'xpath', '//div[@class="tech-section-progress progress"]')
        self.assertEqual(len(progress_indicators), get_category_count())
        buttons = self.findManyBy('xpath', '//a[contains(@href, "edit/cat")]')
        for x in buttons:
            self.assertIn('0/', x.text)
        progress_bars = self.findManyBy(
            'xpath', '//span[@class="meter" and @style="width:0%"]')
        self.assertEqual(len(progress_bars), len(progress_indicators))

        # Alice tries to submit the questionnaire but it is empty and
        # she sees an error message
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "secondary")]')

    def test_textarea_maximum_length(self, mock_get_user_id):

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
        self.findBy('id', 'id_qg_2-0-original_key_2').send_keys("x" * 60)
        self.findBy('id', 'button-submit').click()
        self.findBy('id', 'button-submit').click()

    def test_textarea_preserves_line_breaks(self, mock_get_user_id):

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
        self.findBy('id', 'button-submit').click()

        # She sees the values were submitted with linebreaks
        self.findBy('xpath', '//h3[contains(text(), "Key 2")]')
        details = self.findBy('xpath', '//p[contains(text(), "asdf")]')
        self.assertEqual(details.text, 'asdf\nasdf')

        self.findBy('id', 'button-submit').click()

    def test_nested_subcategories(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_2_position = get_position_of_category('cat_2')

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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 25")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Key 26")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_2_position))
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the step and fills out some fields
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
        self.findBy('id', 'id_qg_19-0-original_key_5').send_keys('Foo')
        self.findBy('id', 'id_qg_20-0-original_key_25').send_keys('')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 25%;"]')
        self.findBy('id', 'id_qg_21-0-original_key_26').send_keys('Bar')
        self.findBy('id', 'id_qg_20-0-original_key_25').send_keys('')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees the values were submitted
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
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
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.assertEqual(self.findBy(
            'id', 'id_qg_19-0-original_key_5').get_attribute('value'), 'Foo')
        self.assertEqual(self.findBy(
            'id', 'id_qg_21-0-original_key_26').get_attribute('value'), 'Bar')
        self.findBy('id', 'id_qg_20-0-original_key_25').send_keys('Faz')

        # She submits the form and sees the values were submitted
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 26")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 25")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')

        # She submits the form completely and sees the values were submitted
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 5")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 26")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 25")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')

    def test_selects_with_chosen(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_1_position = get_position_of_category('cat_1')

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
        self.findBy('id', 'button-submit').click()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 4")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position))
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and no value is selected
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
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

        # # She sees that the form progress was updated
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees that the value was submitted,
        # progress of Category 1 is now updated
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Afghanistan")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position))
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the form and sees that the value is still selected
        # and the progress is updated
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')

        # She submits the entire form and sees the value is on the details page
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 4")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Germany")]]')

    def test_checkbox(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_2_position = get_position_of_category('cat_2')

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
        self.findBy('id', 'button-submit').click()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 13")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_2_position))
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and no checkbox is selected
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 13")]]')

        self.findBy('xpath', '//*[text()[contains(.,"Value 13_1")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_2_position))
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the step and sees that the first checkbox is
        # selected, form progress is at 1
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
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
        self.findBy('id', 'button-submit').click()

        # The overview now shows both values
        self.findBy('xpath', '//*[text()[contains(.,"Key 13")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Value 13_1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_2")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_3")]]')

        # She submits the form and sees that the radio value is stored
        # correctly
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 13")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Value 13_1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_2")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Value 13_3")]]')

    def test_image_checkbox(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_4_position = get_position_of_category('cat_4')

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))

        # She sees that no Checkbox of Key 14 is selected by default
        self.findByNot(
            'xpath', '//input[@name="qg_11-0-key_14" and @checked="checked"]')

        # She sees that the form progress is at 0
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees that no value was submitted,
        # progress of Category 4 is still 0
        self.findBy('id', 'button-submit').click()
        self.findByNot('xpath', '//article//*[text()[contains(.,"Key 14")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_4_position))
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and no checkbox is selected
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')
        self.findByNot(
            'xpath', '//input[@name="qg_11-0-key_14" and @checked="checked"]')

        # She selects a first checkbox and sees that the form progress
        # was updated
        self.findBy(
            'xpath', '(//input[@name="qg_11-0-key_14"])[1]').click()
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 33.3333%;"]')

        # She submits the step and sees that the value was submitted and
        # the form progress on the overview page is updated
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//img[@alt="Value 14_1"]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_4_position))
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the step and sees that the first checkbox is
        # selected, form progress is at 1
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 33.3333%;"]')

        # She deselects the first value and sees that the progress was
        # updated
        self.findBy(
            'xpath', '(//input[@name="qg_11-0-key_14"])[1]').click()
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width: 0%;"]')

        # She then selects the second and third values and submits the
        # form
        self.findBy(
            'xpath', '(//input[@name="qg_11-0-key_14"])[2]').click()
        self.findBy(
            'xpath', '(//input[@name="qg_11-0-key_14"])[3]').click()
        self.findBy('id', 'button-submit').click()

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
        self.findBy('id', 'button-submit').click()
        self.findByNot(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_1"]')
        self.findBy(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_2"]')
        self.findBy(
            'xpath',
            '//div[contains(@class, "output")]/img[@alt="Value 14_3"]')

    def test_measure_conditional(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))

        # She sees the measure box for Key 21
        self.findBy(
            'xpath',
            '//div[@class="button-bar"]/ul/li/input[@name="qg_16-0-key_21"]')

        # She sees that Key 22 and Key 23 are not visible
        key_22 = self.findBy('id', 'id_qg_17-0-key_22_1')
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Key 21')
        self.checkOnPage('medium')
        self.checkOnPage('Value 16_1')
        self.checkOnPage('Key 23')
        self.checkOnPage('Foo')

        # She goes back to the form and sees that the values are still
        # there, Keys 22 and 23 are visible
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_4'}))
        key_22 = self.findBy('id', 'id_qg_17-0-key_22_1')
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
        self.findBy('id', 'button-submit').click()
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        self.checkOnPage('Key 21')
        self.checkOnPage('medium')
        self.checkOnPage('Key 23')
        self.checkOnPage('Bar')

    def test_checkbox_conditional(self, mock_get_user_id):

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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Key 13')
        self.checkOnPage('Value 13_5')
        self.checkOnPage('Key 24')
        self.checkOnPage('Bar')

        # She goes back to the form and sees that the values are still
        # there, Key 24 is visible
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
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
        self.findBy('id', 'button-submit').click()
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        self.checkOnPage('Key 13')
        self.checkOnPage('Value 13_5')
        self.checkOnPage('Key 24')
        self.checkOnPage('Foo')

    def test_conditional_chaining(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

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
        self.findBy('id', 'button-submit').click()

        # She sees all values were submitted correctly
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Key 11')
        self.checkOnPage('Yes')
        self.checkOnPage('Key 27')
        self.checkOnPage('Value 27 C')
        self.checkOnPage('Key 28')
        self.checkOnPage('Foo')

        # She goes back to the form and sees that the values are still
        # there, Keys 27 and 28 are visible
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
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
        self.findBy('id', 'button-submit').click()
        self.findBy('id', 'button-submit').click()
        self.checkOnPage('Key 11')
        self.checkOnPage('Yes')
        self.checkOnPage('Key 27')
        self.checkOnPage('Value 27 C')
        self.checkOnPage('Key 28')
        self.checkOnPage('Foo')

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

    def test_measure_selects(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_2_position = get_position_of_category('cat_2')

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
        self.findBy('id', 'button-submit').click()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 12")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_2_position))
        self.assertIn('0/', progress_indicator.text)

        # She goes back to the questionnaire step and sees that form
        # progress is still at 0 and the row is unselected
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_2_position))
        self.assertIn('1/', progress_indicator.text)

        # She goes back to the step and sees the row is highlighted and
        # low selected, form progress is at 1
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
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
        self.findBy('id', 'button-submit').click()

        # The overview now shows medium and she submits the form
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')

        # She submits the form and sees that the radio value is stored
        # correctly
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')

    def test_measure_selects_repeating(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))

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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"high")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')

        # She goes back to the form and sees the values were populated
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_2'}))
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')

        # She submits the questionnaire and sees the values were submitted
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 12")]]')
        self.findBy('xpath', '//*[text()[contains(.,"medium")]]')
        self.findBy('xpath', '//*[text()[contains(.,"low")]]')

    def test_radio_selects(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_1_position = get_position_of_category('cat_1')

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        # She sees that Key 11 is a radio button
        radios = self.findManyBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @type="radio"]')
        self.assertEqual(len(radios), 2)

        # She sees that the form does not have any progress
        self.findBy('xpath', '//span[@class="meter" and @style="width:0%"]')

        # She submits the form empty and sees no value was submitted,
        # progress of Category 1 is still 0
        self.findBy('id', 'button-submit').click()
        self.findByNot('xpath', '//*[text()[contains(.,"Key 11")]]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position))
        self.assertIn('0/', progress_indicator.text)

        # She goes to the form again and clicks "Yes".
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @value="1"]')\
            .click()

        # She sees that the progress was updated and submits the form.
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')

        self.findBy('id', 'button-submit').click()

        # She sees the value was transmitted and the progress was updated
        self.findBy('xpath', '//*[text()[contains(.,"Key 11")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Yes")]]')
        self.findBy(
            'xpath', '//span[@class="meter" and @style="width:50%"]')
        progress_indicator = self.findBy(
            'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
                cat_1_position))
        self.assertIn('1/2', progress_indicator.text)

        # She edits the form again and sets the radio button to "No"
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')
        self.findBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @value="1" and '
            '@checked=""]')
        self.findBy(
            'xpath', '//input[@name="qg_3-0-key_11" and @value="0"]')\
            .click()
        self.findBy('id', 'button-submit').click()

        # She sees the value was updated
        self.findBy('xpath', '//*[text()[contains(.,"Key 11")]]')
        self.findBy('xpath', '//*[text()[contains(.,"No")]]')

        # She submits the form and sees the radio value is stored correctly
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//*[text()[contains(.,"Key 11")]]')
        self.findBy('xpath', '//*[text()[contains(.,"No")]]')

    def test_plus_questiongroup(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

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
        time.sleep(1)
        self.assertTrue(key_37.is_displayed())
        self.assertTrue(key_38.is_displayed())

        # She enters some text and sees that the progress was updated
        key_37.send_keys('Foo')
        key_38.send_keys('Bar')
        self.findBy('xpath', '//span[@class="meter" and @style="width: 50%;"]')

        # She submits the form and sees that the values were submitted
        # correctly.
        self.findBy('id', 'button-submit').click()
        self.checkOnPage('Foo')
        self.checkOnPage('Bar')

        # She goes back to the form and sees the additional
        # questiongroups are now visible because they have initial
        # values
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

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
        time.sleep(1)
        self.assertFalse(key_37.is_displayed())
        self.assertFalse(key_38.is_displayed())
        plus_button.click()
        time.sleep(1)

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
        self.findBy('id', 'button-submit').click()
        self.checkOnPage('Foo')
        self.checkOnPage('Bar')

        self.findBy('id', 'button-submit').click()
        self.checkOnPage('Foo')
        self.checkOnPage('Bar')

    def test_table_entry(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire with a table
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_5'}))

        # She sees a table and enters some values
        table = self.findBy('xpath', '//table')

        headers = self.findManyBy('xpath', '//th', base=table)
        self.assertEqual(len(headers), 4)
        self.assertEqual(headers[0].text, 'Key 33')
        self.assertEqual(headers[1].text, 'Key 34')
        self.assertEqual(headers[2].text, 'Key 35')
        self.assertEqual(headers[3].text, 'Key 36')

        row_1 = self.findBy('xpath', '//tr[1]', base=table)
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

        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

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

        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

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

    def test_header_image(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

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
        self.findBy('id', 'button-submit').click()

        # On the overview page, she sees the image she uploaded
        self.findBy('xpath', '//img[@data-interchange]')

        # She edits the form again and sees the image was populated correctly.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # Dropzone is hidden, preview is there, filename was written to field
        dropzone = self.findBy(
            'xpath', '//div[@id="id_qg_14-0-file_key_19" and contains(@class, '
            '"dropzone")]')
        time.sleep(2)
        self.assertFalse(dropzone.is_displayed())
        preview = self.findBy(
            'xpath', '//div[@id="preview-id_qg_14-0-file_key_19"]')
        self.assertTrue(preview.is_displayed())
        filename = self.findBy('xpath', '//input[@id="id_qg_14-0-key_19"]')
        self.assertNotEqual(filename.get_attribute('value'), '')

        # She submits the form and sees that the image was submitted correctly.
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//img[@data-interchange]')

        self.findBy('id', 'button-submit').click()

    @attr('foo')
    def test_upload_multiple_images(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_3'}))

        # She sees a field to put files, drawn by Dropzone
        dropzone = self.findBy(
            'xpath', '//div[@id="id_qg_30-0-file_key_19" and contains(@class, '
            '"dropzone")]')
        self.assertTrue(dropzone.is_displayed())

        # She does not see the preview field, which is hidden and does not
        # contain an image
        preview = self.findBy(
            'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]')
        self.assertFalse(preview.is_displayed())
        self.findByNot(
            'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]/'
            'div[@class="image-preview"]/img')

        # The hidden input field is empty
        filename = self.findBy('xpath', '//input[@id="id_qg_30-0-key_19"]')
        self.assertEqual(filename.get_attribute('value'), '')

        # She uploads an image
        self.dropImage('id_qg_30-0-file_key_19')

        # She sees that the dropzone is hidden, the preview is visible
        self.assertFalse(dropzone.is_displayed())
        self.assertTrue(preview.is_displayed())

        # Preview contains an image
        self.findBy(
            'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]/'
            'div[@class="image-preview"]/img')

        # The filename was added to the hidden input field
        self.assertNotEqual(filename.get_attribute('value'), '')

        # She adds another image
        self.findBy(
            'xpath', '//a[@data-questiongroup-keyword="qg_30"]').click()

        # She sees that another dropzone was added and it is empty.
        dropzone_2 = self.findBy(
            'xpath', '//div[@id="id_qg_30-1-file_key_19" and contains(@class, '
            '"dropzone")]')
        preview_2 = self.findBy(
            'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]')
        # self.findByNot(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # import time
        # time.sleep(1)
        # self.assertTrue(dropzone_2.is_displayed())
        # self.assertFalse(preview_2.is_displayed())
        #
        # # She submits the form and sees only one image was submitted
        # self.findBy('id', 'button-submit').click()
        #
        # # On the overview page, she sees the image she uploaded
        # images = self.findManyBy(
        #     'xpath', '//div[contains(@class, "output")]/img')
        # self.assertEqual(len(images), 1)
        #
        # # She edits the form again and sees the image was populated correctly.
        # self.browser.get(self.live_server_url + reverse(
        #     route_questionnaire_new_step,
        #     kwargs={'identifier': 'new', 'step': 'cat_3'}))
        #
        # # Dropzone is hidden, preview is there, filename was written to field
        # dropzone = self.findBy(
        #     'xpath', '//div[@id="id_qg_30-0-file_key_19" and contains(@class, '
        #     '"dropzone")]')
        # time.sleep(1)
        # self.assertFalse(dropzone.is_displayed())
        # preview = self.findBy(
        #     'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]')
        # self.assertTrue(preview.is_displayed())
        # filename = self.findBy('xpath', '//input[@id="id_qg_30-0-key_19"]')
        # self.assertNotEqual(filename.get_attribute('value'), '')
        #
        # # She adds another image
        # self.findBy(
        #     'xpath', '//a[@data-questiongroup-keyword="qg_30"]').click()
        #
        # # She sees that another dropzone was added and it is empty.
        # dropzone_2 = self.findBy(
        #     'xpath', '//div[@id="id_qg_30-1-file_key_19" and contains(@class, '
        #     '"dropzone")]')
        # preview_2 = self.findBy(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]')
        # self.findByNot(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # # She uploads a second image
        # self.dropImage('id_qg_30-1-file_key_19')
        #
        # # The hidden input field is empty
        # filename_2 = self.findBy('xpath', '//input[@id="id_qg_30-1-key_19"]')
        #
        # # She sees that the dropzone is hidden, the preview is visible
        # self.assertFalse(dropzone_2.is_displayed())
        # self.assertTrue(preview_2.is_displayed())
        #
        # # Preview contains an image
        # self.findBy(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # # The filename was added to the hidden input field
        # self.assertNotEqual(filename_2.get_attribute('value'), '')
        #
        # # She removes the second image again
        # self.findBy(
        #     'xpath',
        #     '//div[@id="preview-id_qg_30-1-file_key_19"]/div/button').click()
        #
        # # She sees the preview is empty
        # self.findBy(
        #     'xpath', '//div[@id="id_qg_30-1-file_key_19" and contains(@class, '
        #     '"dropzone")]')
        # self.findByNot(
        #     'xpath',
        #     '//div[@id="id_qg_30-1-file_key_19"]//div[@class="dz-image"]')
        # self.findByNot(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # # She submits and sees the correct image was submitted
        # self.findBy('id', 'button-submit').click()
        #
        # img = self.findManyBy('xpath', '//div[contains(@class, "output")]/img')
        # self.assertEqual(len(img), 1)
        #
        # db_images = File.objects.all()
        # self.assertEqual(len(db_images), 2)
        #
        # should_image = db_images[0]
        # self.assertTrue(should_image.uuid in img[0].get_attribute("src"))
        #
        # # She goes back to the form
        # self.browser.get(self.live_server_url + reverse(
        #     route_questionnaire_new_step,
        #     kwargs={'identifier': 'new', 'step': 'cat_3'}))
        #
        # # She adds another image
        # self.findBy(
        #     'xpath', '//a[@data-questiongroup-keyword="qg_30"]').click()
        # self.dropImage('id_qg_30-1-file_key_19')
        #
        # # She submits the step and sees both images are there
        # self.findBy('id', 'button-submit').click()
        #
        # # On the overview page, she sees the image she uploaded
        # images = self.findManyBy(
        #     'xpath', '//div[contains(@class, "output")]/img')
        # self.assertEqual(len(images), 2)
        #
        # # She edits the form again
        # self.browser.get(self.live_server_url + reverse(
        #     route_questionnaire_new_step,
        #     kwargs={'identifier': 'new', 'step': 'cat_3'}))
        # import time
        # time.sleep(1)
        #
        # # She removes the second image
        # self.findBy(
        #     'xpath',
        #     '//div[@id="preview-id_qg_30-1-file_key_19"]/div/button').click()
        #
        # # The preview is now empty
        # self.findBy(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]')
        #
        # preview_2 = self.findByNot(
        #     'xpath', '//div[@id="preview-id_qg_30-1-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # # She submits the step and sees the image is there
        # self.findBy('id', 'button-submit').click()
        # self.findBy('xpath', '//div[contains(@class, "success")]')
        #
        # # On the overview page, she sees the image she uploaded
        # images = self.findManyBy(
        #     'xpath', '//div[contains(@class, "output")]/img')
        # self.assertEqual(len(images), 1)
        #
        # # She goes back to edit the form again
        # self.browser.get(self.live_server_url + reverse(
        #     route_questionnaire_new_step,
        #     kwargs={'identifier': 'new', 'step': 'cat_3'}))
        # import time
        # time.sleep(1)
        #
        # # She adds another image
        # self.findBy(
        #     'xpath', '//a[@data-questiongroup-keyword="qg_30"]').click()
        # self.dropImage('id_qg_30-1-file_key_19')
        #
        # # She decides to remove the second questiongroup again
        # self.findBy(
        #     'xpath', '//div[@data-questiongroup-keyword="qg_30"][2]//a['
        #     'contains(@class, "list-item-action")]').click()
        #
        # # One image remains
        # self.findBy(
        #     'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # # She removes the remaining image and adds a new one
        # self.findBy(
        #     'xpath',
        #     '//div[@id="preview-id_qg_30-0-file_key_19"]/div/button').click()
        # import time
        # time.sleep(1)
        #
        # self.findBy(
        #     'xpath', '//div[@id="id_qg_30-0-file_key_19" and contains(@class, '
        #     '"dropzone")]')
        # preview_1 = self.findBy(
        #     'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]')
        # self.assertFalse(preview_1.is_displayed())
        # self.findByNot(
        #     'xpath', '//div[@id="preview-id_qg_30-0-file_key_19"]/'
        #     'div[@class="image-preview"]/img')
        #
        # self.dropImage('id_qg_30-0-file_key_19')
        #
        # # She submits the entire form and sees the image is there.
        # self.findBy('id', 'button-submit').click()
        # self.findBy('xpath', '//div[contains(@class, "success")]')
        #
        # # On the overview page, she sees the image she uploaded
        # images = self.findManyBy(
        #     'xpath', '//div[contains(@class, "output")]/img')
        # self.assertEqual(len(images), 1)

    def test_edit_questionnaire(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_1_position = get_position_of_category('cat_1', start0=True)

        # She goes directly to the first category of the Sample
        # questionnaire and enters some data
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.findBy('id', 'button-submit').click()

        # She submits the entire questionnaire and clicks the edit
        # button on the detail page
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()

        # She is back at the overview page of the questionnaire with the
        # previously entered values already there
        self.findBy('xpath', '//*[text()[contains(.,"Key 1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Key 3")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')

        # She edits a form and sees the values are there already
        self.findManyBy(
            'xpath',
            '//a[contains(@href, "edit/sample_0/cat")]')[
                cat_1_position].click()
        key_1 = self.findBy('name', 'qg_1-0-original_key_1')
        self.assertEqual(key_1.get_attribute('value'), 'Foo')
        key_3 = self.findBy('name', 'qg_1-0-original_key_3')
        self.assertEqual(key_3.get_attribute('value'), 'Bar')
        key_1.clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Faz')

        # She submits the step and sees that the values on the overview
        # page changed.
        self.findBy('id', 'button-submit').click()
        self.findByNot('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')

        # She submits the entire questionnaire
        self.findBy('id', 'button-submit').click()


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
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

    def test_enter_questionnaire(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        cat_1_position = get_position_of_category('cat_1', start0=True)

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

        # She tries to submit the form empty and sees an error message
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "secondary")]')

        # She sees X buttons to edit a category and clicks the first
        edit_buttons = self.findManyBy(
            'xpath', '//a[contains(@href, "edit/new/cat")]')
        self.assertEqual(len(edit_buttons), get_category_count())
        edit_buttons[cat_1_position].click()

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
        self.findBy('id', 'button-submit').click()

        # She sees that she was redirected to the overview page and is
        # shown a success message
        self.findBy('xpath', '//div[contains(@class, "success")]')
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

        # She sees the author is still not filled out
        self.findByNot(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/a['
            'contains(text(), "bar foo")]')

        # She submits the entire questionnaire
        self.findBy('id', 'button-submit').click()

        # She is being redirected to the details page and sees a success
        # message.
        self.findBy('xpath', '//div[contains(@class, "success")]')
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

        # She sees the author is now filled out
        self.findBy(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/a['
            'contains(text(), "bar foo")]')

        # She sees that the # was removed from the URL
        self.assertIn('#top', self.browser.current_url)

        # She sees that on the detail page, there is only one edit button
        edit_buttons = self.findManyBy(
            'xpath', '//a[contains(text(), "Edit")]')
        self.assertEqual(len(edit_buttons), 1)

        # She goes to the list of questionnaires and sees that the
        #  questionnaire she created is listed there.
        self.findBy('xpath', '//a[contains(@href, "{}")]'.format(
            reverse(route_questionnaire_list))).click()
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


@patch.object(Typo3Client, 'get_user_id')
class QuestionnaireLinkTest(FunctionalTest):

    fixtures = [
        'sample_global_key_values.json', 'sample.json', 'samplemulti.json',
        'sample_samplemulti_questionnaires.json']

    def test_add_questionnaire_link(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a part of the questionnaire and enters some data
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She goes to the part where she can edit linked questionnaires
        self.findBy('xpath', '//a[contains(@href, "/edit/new/link")]').click()

        # She sees a field to search for linked questionnaires
        self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")]'
            '[1]').send_keys('key')
        time.sleep(1)
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
        # She sees that a hidden field with the id was added
        self.findBy('xpath', '//input[@id="links__samplemulti__3"]')

        # She removes the link and then adds it again
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()
        self.findByNot('xpath', '//input[@id="links__samplemulti__3"]')
        self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")]'
            '[1]').send_keys('key')
        time.sleep(1)
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is key 1a"'
            ']').click()

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that the link was added in category 6
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1a")]]')

        # She goes back to the form and sees the one she linked is still
        # in the form.
        self.findBy('xpath', '//a[contains(@href, "/edit/new/link")]').click()
        self.findBy('xpath', '//input[@id="links__samplemulti__3"]')
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is key 1a")]')

        # She deletes the link and submits the form
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()
        self.findByNot('xpath', '//input[@id="links__samplemulti__3"]')

        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findByNot('xpath', '//*[text()[contains(.,"This is key 1a")]]')

        # She links another questionnaire
        self.findBy('xpath', '//a[contains(@href, "/edit/new/link")]').click()
        self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")]'
            '[1]').send_keys('key')
        time.sleep(1)
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is key 1b"]').\
            click()

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that the link was added in category 6
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1b")]]')

        # She submits the complete form
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that the link was added in category 6
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1b")]]')

        # The link can be clicked
        self.findBy(
            'xpath', '//a[contains(@href, "samplemulti/view/")]').click()
        self.checkOnPage('MSection')

        # There is a link back
        self.findBy('xpath', '//a[contains(@href, "sample/view/")]')

    def test_edit_questionnaire_link(self, mock_get_user_id):

        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She opens an existing questionnaire and sees the link
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, args=['sample_1']))

        self.findBy('xpath', '//*[text()[contains(.,"This is key 1a")]]')
        self.findBy(
            'xpath', '//a[contains(@href, "samplemulti/view/")]').click()
        self.findBy('xpath', '//a[contains(@href, "sample/view/")]').click()

        # She decides to edit the questionnaire
        self.findBy('xpath', '//a[contains(@href, "sample/edit/")]').click()

        # She sees the link in the edit overview
        self.findBy('xpath', '//h2[text()="Linked Questionnaires"]')
        self.findBy('xpath', '//*[text()[contains(.,"This is key 1a")]]')

        # She edits the link form and sees the values are populated correctly
        self.findBy(
            'xpath', '//a[contains(@href, "/edit/sample_1/link")]').click()
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is key 1a")]')
        self.findBy('xpath', '//input[@id="links__samplemulti__3"]')

        # She deletes the link and submits the entire form
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()

        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//h2[text()="Linked Questionnaires"]')

        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        self.findByNot('xpath', '//h2[text()="Linked Questionnaires"]')

    def test_edit_questionnaire_multiple_links(self, mock_get_user_id):

        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She opens an existing questionnaire (samplemulti) and sees the link
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details_samplemulti, args=['samplemulti_1']))

        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')

        # She decides to edit the questionnaire
        self.findBy(
            'xpath', '//a[contains(@href, "samplemulti/edit/")]').click()

        # She sees the link in the edit overview
        self.findBy('xpath', '//h2[text()="Linked Questionnaires"]')
        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')

        # She decides to edit the link and sees that the field is
        # populated correctly
        self.findBy(
            'xpath',
            '//a[contains(@href, "/edit/samplemulti_1/link")]').click()
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"This is the first key")]')
        self.findBy('xpath', '//input[@id="links__sample__1"]')

        # She tries to add the same link again, this does not work.
        self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")]'
            '[1]').send_keys('key')
        time.sleep(1)
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="This is the first '
            'key."]').click()
        x = self.findManyBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            ' "This is the first key")]')
        self.assertEqual(len(x), 1)
        self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")]'
            '[1]').clear()

        # She adds another link
        self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")]'
            '[1]').send_keys('foo')
        time.sleep(1)
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"]').\
            click()

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that both links were added
        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')

        # She submits the form and sees that both links were correctly
        # submitted.
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy(
            'xpath', '//*[text()[contains(.,"This is the first key")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')

    @patch('samplemulti.views.generic_questionnaire_link_search')
    def test_search(self, mock_link_search, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to the link section of a new questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_link_form, kwargs={'identifier': 'new'}))

        search_field = self.findBy(
            'xpath', '//input[contains(@class, "link_search_field")][1]')

        mock_link_search.return_value = JsonResponse({
            'total': 0,
            'data': []
        })
        search_field.send_keys('foo')
        time.sleep(1)
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
        time.sleep(1)
        # She gets a message saying there are too many results to
        # display them all. Clicking on the message does not do
        # anything. Not all results are shown.
        results = self.findManyBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="foo"]')
        self.assertEqual(len(results), 10)
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[contains(text(), "Too many '
            'results")]'
        ).click()
        self.findByNot(
            'xpath',
            '//div[contains(@class, "alert-box")]')

        empty = self.findBy(
            'xpath', '//*[contains(text(), "No linked Questionnaires")]')
        self.assertTrue(empty.is_displayed())

        search_field.clear()
        search_field.send_keys('foo')
        time.sleep(1)
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="foo"][1]').click()
        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")]')

        empty = self.findBy(
            'xpath', '//*[contains(text(), "No linked Questionnaires")]')
        self.assertFalse(empty.is_displayed())

        self.findBy(
            'xpath',
            '//div[contains(@class, "alert-box")][1]/a[@class="close"]')\
            .click()
        empty = self.findBy(
            'xpath', '//*[contains(text(), "No linked Questionnaires")]')
        self.assertTrue(empty.is_displayed())

    """
    Test:
    * Show pending
    """
