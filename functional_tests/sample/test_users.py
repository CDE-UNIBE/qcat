from accounts.middleware import WocatAuthenticationMiddleware
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse

from accounts.tests.test_models import create_new_user
from questionnaire.tests.test_models import get_valid_questionnaire

from functional_tests.base import FunctionalTest

from accounts.client import Typo3Client
from accounts.models import User
from accounts.tests.test_views import accounts_route_questionnaires
from django.test.utils import override_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from unittest.mock import patch

from questionnaire.models import Questionnaire
from sample.tests.test_views import (
    route_questionnaire_new_step,
)

TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@patch.object(Typo3Client, 'get_user_id')
class UserTest(FunctionalTest):

    fixtures = [
        'groups_permissions.json', 'global_key_values.json', 'sample.json',
        'sample_questionnaire_status.json']

    """
    status:
    1: draft
    2: submitted
    3: reviewed
    4: public
    5: rejected
    6: inactive

    user:
    101: user
    102: user
    103: reviewer
    104: publisher
    105: reviewer, publisher
    106: user

    id: 1   code: sample_1   version: 1   status: 1   user: 101
        (draft by user 101)

    id: 2   code: sample_2   version: 1   status: 2   user: 102
        (submitted by user 102)

    id: 3   code: sample_3   version: 1   status: 4   user: 101, 102
        (public by user 101 and 102)

    id: 4   code: sample_4   version: 1   status: 5   user: 101
        (rejected)

    id: 5   code: sample_5   version: 1   status: 6   user: 101
        (inactive version of 6)

    id: 6   code: sample_5   version: 2   status: 4   user: 101
        (public version of 5 by user 101)

    id: 7   code: sample_6   version: 1   status: 1   user: 103
        (draft by user 103)

    id: 8   code: sample_7   version: 1   status: 3   user: 101
        (reviewed by user 101)

    id: 9   code: sample_8   version: 1   status: 2   user: 101, (102)
        (submitted by user 101, assigned to user 102)

    id: 10  code: sample_9   version: 1   status: 3   user: 101, (106)
        (reviewed by user 101, assigned to user 106)
    """

    def test_user_questionnaires(self, mock_get_user_id):

        user_alice = User.objects.get(pk=101)
        user_bob = User.objects.get(pk=102)

        # Alice logs in
        self.doLogin(user=user_alice)

        # She sees and clicks the link in the user menu to view her
        # Questionnaires
        self.clickUserMenu(user_alice)
        self.findBy(
            'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
            'contains(@href, "accounts/questionnaires")]').click()

        # She sees here Questionnaires are listed, even those with
        # status draft or submitted
        self.wait_for(
            'xpath', '//img[@src="/static/assets/img/ajax-loader.gif"]',
            visibility=False)

        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 6)

        # The questionnaires are grouped by status
        # Draft
        self.findBy('xpath', '(//div[contains(@class, "tech-group")])[2]'
                             '/h2[text()="Draft"]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//a['
            'contains(text(), "Foo 1")]')

        # Submitted
        self.findBy('xpath', '(//div[contains(@class, "tech-group")])[3]'
                             '/h2[text()="Submitted"]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//a['
                     'contains(text(), "Foo 8")]')

        # Reviewed
        self.findBy('xpath', '(//div[contains(@class, "tech-group")])[4]'
                             '/h2[text()="Reviewed"]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[3]//a['
                     'contains(text(), "Foo 7")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[4]//a['
                     'contains(text(), "Foo 9")]')

        # Public
        self.findBy('xpath', '(//div[contains(@class, "tech-group")])[5]'
                             '/h2[text()="Public"]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[5]//a['
            'contains(text(), "Foo 3")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[6]//a['
            'contains(text(), "Foo 5")]')

        # # She goes to the questionnaire page of Bob and sees the
        # # Questionnaires of Bob but only the "public" ones.
        # self.browser.get(self.live_server_url + reverse(
        #     accounts_route_questionnaires, kwargs={'user_id': 102}))
        # list_entries = self.findManyBy(
        #     'xpath', '//article[contains(@class, "tech-item")]')
        # self.assertEqual(len(list_entries), 2)
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
        #     'contains(text(), "Foo 3")]')
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
        #     'contains(text(), "Foo 8")]')

        # # She logs out and sees the link in the menu is no longer visible.
        # self.doLogout()
        # self.findByNot(
        #     'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
        #     'contains(@href, "accounts/101/questionnaires")]')
        #
        # # On her Questionnaire page only the "public" Questionnaires are
        # # visible.
        # self.browser.get(self.live_server_url + reverse(
        #     accounts_route_questionnaires, kwargs={'user_id': 101}))
        # list_entries = self.findManyBy(
        #     'xpath', '//article[contains(@class, "tech-item")]')
        # self.assertEqual(len(list_entries), 2)
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
        #     'contains(text(), "Foo 3")]')
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
        #     'contains(text(), "Foo 5")]')

        # Bob logs in and goes to his Questionnaire page. He sees all
        # versions of his Questionnaires.
        self.doLogin(user=user_bob)
        self.clickUserMenu(user_bob)
        self.findBy(
            'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
                     'contains(@href, "accounts/questionnaires")]').click()
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)

        # The questionnaires are grouped by status

        # Submitted
        self.findBy('xpath', '(//div[contains(@class, "tech-group")])[2]'
                             '/h2[text()="Submitted"]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//a['
            'contains(text(), "Foo 2")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//a['
            'contains(text(), "Foo 8")]')

        # # He goes to the Questionnaire page of Alice and only sees the
        # # "public" Questionnaires.
        # self.browser.get(self.live_server_url + reverse(
        #     accounts_route_questionnaires, kwargs={'user_id': 101}))
        # list_entries = self.findManyBy(
        #     'xpath', '//article[contains(@class, "tech-item")]')
        # self.assertEqual(len(list_entries), 3)
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
        #     'contains(text(), "Foo 3")]')
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
        #     'contains(text(), "Foo 5")]')
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[3]//h1/a['
        #     'contains(text(), "Foo 8")]')

        # # He goes to the Questionnaire page of Chris and sees no
        # # "public" Questionnaires with an appropriate message.
        # self.browser.get(self.live_server_url + reverse(
        #     accounts_route_questionnaires, kwargs={'user_id': 103}))
        # list_entries = self.findManyBy(
        #     'xpath', '//article[contains(@class, "tech-item")]')
        # self.assertEqual(len(list_entries), 0)
        # self.findBy(
        #     'xpath', '//p[@class="questionnaire-list-empty" and contains('
        #     'text(), "No WOCAT and UNCCD SLM practices found.")]')


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch('wocat.views.generic_questionnaire_list')
@patch.object(Typo3Client, 'get_user_id')
class UserTest2(FunctionalTest):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def test_add_user(self, mock_get_user_id, mock_questionnaire_list):

        mock_questionnaire_list.return_value = {}

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))
        self.rearrangeFormHeader()

        # She does not see a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]')
        self.assertFalse(search_user.is_displayed())

        # She clicks on the radio to search fo an existing user
        search_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="search"]')
        search_radio.click()

        # There is no loading indicator
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())

        # She enters a name and sees a search is conducted
        search_user.send_keys('kurt')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))

        # She clicks a result
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Kurt Gerber"]'
        ).click()

        # She sees a loading indicator while the user is updated in the DB
        self.assertTrue(loading_indicator.is_displayed())

        # She waits until the loading indicator disappears
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        # She sees that the search field is not visible anymore
        self.assertFalse(search_user.is_displayed())

        # She sees that a field with the name was added
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Kurt Gerber")]')

        # She sees that a hidden field with the id was added
        self.findBy(
            'xpath', '//input[@id="id_qg_31-0-key_39" and @value="1055"]')

        # She removes the user
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Kurt Gerber")]/a').click()

        # The user is removed and the search box is visible again
        self.findByNot(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Kurt Gerber")]')
        self.assertTrue(search_user.is_displayed())

        # She hidden field does not contain the ID anymore
        self.findByNot(
            'xpath', '//input[@id="id_qg_31-0-key_39" and @value="1055"]')

        # She selects the user again
        search_user.send_keys('kurt')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Kurt Gerber"]'
        ).click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        # She submits the step
        self.submit_form_step()

        # She sees the name is in the overview
        self.checkOnPage('Kurt Gerber')

        # She goes back to the form
        self.click_edit_section('cat_0')

        # She sees the user is selected, loading and search fields are
        # not visible
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Kurt Gerber")]')
        self.findBy(
            'xpath', '//input[@id="id_qg_31-0-key_39" and @value="1055"]')

        # She removes the user and selects another one
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Kurt Gerber")]/a').click()

        self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]'
            '[1]').send_keys('lukas')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Lukas Vonlanthen"]'
        ).click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        # She submits the step
        self.submit_form_step()
        self.checkOnPage('Lukas Vonlanthen')

        # She submits the entire questionnaire and sees the name is there
        self.review_action('submit')
        self.checkOnPage('Lukas Vonlanthen')

        # She checks the database to make sure the user was added.
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()
        self.assertEqual(len(questionnaire_users), 2)
        for user_tuple in questionnaire_users:
            self.assertIn(user_tuple[0], ['compiler', 'landuser'])
            self.assertIn(user_tuple[1].id, [1, 2365])

    def test_add_new_person(self, mock_get_user_id, mock_questionnaire_list):

        mock_questionnaire_list.return_value = {}
        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))
        self.rearrangeFormHeader()

        # She does not see a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]')
        self.assertFalse(search_user.is_displayed())

        # She does not see a field to add new personas either
        new_name = self.findBy('id', 'id_qg_31-0-original_key_41')
        self.assertFalse(new_name.is_displayed())

        # She sees two radio buttons
        search_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="search"]')
        create_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="create"]')

        # She clicks on the radio to enter a new persona and sees that the input
        # field is visible
        create_radio.click()
        self.assertTrue(new_name.is_displayed())

        # She decides to search for a user first
        search_radio.click()
        self.assertFalse(new_name.is_displayed())

        # There is no loading indicator
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())

        # Before she starts searching, she enters something in the text field
        # above
        textfield_above = self.findBy('name', 'qg_31-0-original_key_45')
        textfield_above.send_keys('foo')

        # She enters a name and sees a search is conducted
        search_user.send_keys('abcdefghijklmnopq')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))

        # She sees there is no result
        no_results = self.findBy(
            'xpath', '//li[contains(@class, "ui-menu-item")]//strong['
            'contains(text(), "No results found")]')
        # She clicks the "no results" entry but nothing happens
        no_results.click()

        self.assertFalse(loading_indicator.is_displayed())

        # She decides to enter a new person
        create_radio.click()
        new_name.send_keys('New Person')
        self.assertEqual(new_name.get_attribute('value'), 'New Person')
        self.findBy(
            'xpath', '//div[@id="id_qg_31_0_key_4_chosen"]').click()
        self.findBy(
            'xpath', '//ul[@class="chosen-results"]/li[text()="Afghanistan"]')\
            .click()
        chosen_field = self.findBy('xpath', '//div[@id="id_qg_31_0_key_4_chosen"]/a[@class="chosen-single"]')  # noqa
        self.assertEqual(chosen_field.text, 'Afghanistan')

        # She is having second thoughts and decides to search for a
        # person once again
        search_radio.click()
        search_user.clear()
        search_user.send_keys('lukas')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Lukas Vonlanthen"]'
        ).click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        # She sees that the user was selected
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]')

        # She sees that the text she entered in the textfield above is still
        # there
        self.assertEqual(textfield_above.get_attribute('value'), 'foo')

        # She goes back to the select tab and sees that the values she
        # entered previously are gone now
        create_radio.click()
        self.assertEqual(new_name.get_attribute('value'), '')
        self.assertEqual(chosen_field.text, '-')

        # She enters a new name
        new_name.send_keys('Other New Person')
        self.findBy('xpath', '//html').click()  # Lose focus
        self.assertTrue(new_name.is_displayed())

        # She goes back to the other tab and sees the selected user is gone
        search_radio.click()
        self.findByNot(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]')

        # She submits the step
        self.submit_form_step()

        # She sees the new person was submitted correctly
        self.checkOnPage('Other New Person')
        self.findByNot('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # She goes back to the form
        self.click_edit_section('cat_0')

        # She sees the tab with the new user details is shown
        new_name = self.findBy('id', 'id_qg_31-0-original_key_41')
        self.assertTrue(new_name.is_displayed())
        self.assertEqual(new_name.get_attribute('value'), 'Other New Person')

        search_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="search"]')
        create_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="create"]')

        # She sees that there is no box with the user in the registered tab and
        # there is no loading indicator
        search_radio.click()
        self.findByNot(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]')
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())

        # She changes the value of the new person
        create_radio.click()
        new_name.clear()
        new_name.send_keys('Person A')

        # She submits the step
        self.submit_form_step()
        self.checkOnPage('Person A')

        # She submits the entire questionnaire and sees the name is there
        self.review_action('submit')
        self.checkOnPage('Person A')

        # She checks the database to make sure no additional user was added.
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()
        self.assertEqual(len(questionnaire_users), 1)
        self.assertEqual(questionnaire_users[0][0], 'compiler')
        self.assertEqual(questionnaire_users[0][1].id, 1)

    def test_add_multiple_users_persons(self, mock_get_user_id,
                                        mock_questionnaire_list):

        mock_questionnaire_list.return_value = {}
        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))
        self.rearrangeFormHeader()

        # She does not see a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]')
        self.assertFalse(search_user.is_displayed())

        # She does not see a field to add new personas either
        new_name = self.findBy('id', 'id_qg_31-0-original_key_41')
        self.assertFalse(new_name.is_displayed())

        # She sees two radio buttons
        search_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="search"]')
        create_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="create"]')

        # She clicks the radio to search for a user
        search_radio.click()

        # There is no loading indicator
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())

        # She enters a first user by search
        search_user.send_keys('kurt')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Kurt Gerber"]'
        ).click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        # She adds a second person
        self.findBy(
            'xpath', '//fieldset[contains(@class, "row")][2]//a['
            'contains(@class, "link") and @data-questiongroup-keyword='
            '"qg_31"]').click()

        # She sees that the second group does not show neither search field nor
        # create field.
        qg_2_xpath = '//fieldset[@id="subcat_0_2"]//div[contains(@class, ' \
                     '"list-item")][2]'

        # She does not see a field to search for users
        search_user_2 = self.findBy(
            'xpath', '{}//input[contains(@class, "user-search-field")]'.format(
                qg_2_xpath))
        self.assertFalse(search_user_2.is_displayed())

        # She does not see a field to add new personas either
        new_name = self.findBy('id', 'id_qg_31-1-original_key_41')
        self.assertFalse(new_name.is_displayed())

        # No user is selected
        self.findByNot(
            'xpath', '{}//div[contains(@class, "form-user-selected")]/div['
            'contains(@class, "secondary")]'.format(qg_2_xpath))

        # She sees two radio buttons
        search_radio_2 = self.findBy(
            'xpath', '{}//input[@name="form-user-radio" and @value="search"]'.
                     format(qg_2_xpath))
        create_radio_2 = self.findBy(
            'xpath', '{}//input[@name="form-user-radio" and @value="create"]'.
                     format(qg_2_xpath))

        # She clicks the radio to create a new persona
        create_radio_2.click()

        # She adds the second user as a non-registered person
        self.findBy('id', 'id_qg_31-1-original_key_41').send_keys(
            'Some Person')

        # She adds a third person
        self.findBy(
            'xpath', '//fieldset[contains(@class, "row")][2]//a['
            'contains(@class, "link") and @data-questiongroup-keyword='
            '"qg_31"]').click()

        # She sees that the third group shows the search field by
        # default, no user is selected
        qg_3_xpath = '//fieldset[@id="subcat_0_2"]//div[contains(@class, ' \
                     '"list-item")][3]'

        search_radio_3 = self.findBy(
            'xpath', '{}//input[@name="form-user-radio" and @value="search"]'.
                     format(qg_3_xpath))
        search_radio_3.click()

        search_user_3 = self.findBy(
            'xpath', '{}//input[contains(@class, "user-search-field")]'.format(
                qg_3_xpath))
        self.assertTrue(search_user_3.is_displayed())

        self.findByNot(
            'xpath', '{}//div[contains(@class, "form-user-selected")]/div['
            'contains(@class, "secondary")]'.format(qg_3_xpath))

        # There is no loading indicator
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())

        # She enters a first user by search
        search_user_3.send_keys('lukas')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((
                By.XPATH, '//ul[contains(@class, "ui-autocomplete")][3]/li['
                'contains(@class, "ui-menu-item")]')))
        self.findBy(
            'xpath',
            '//ul[contains(@class, "ui-autocomplete")][3]/li[contains(@class, '
            '"ui-menu-item")]//strong[text()="Lukas Vonlanthen"]'
        ).click()

        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.XPATH, '{}//div[contains(@class, "form-user-search-'
                'loading")]'.format(qg_3_xpath))))

        # She submits the step
        self.submit_form_step()

        # She sees all the values are in the overview
        self.checkOnPage('Kurt Gerber')
        self.checkOnPage('Some Person')
        self.checkOnPage('Lukas Vonlanthen')

        # She goes back to the form
        self.click_edit_section('cat_0')

        # She sees that the form was populated correctly
        qg_1_xpath = (
            '//fieldset[contains(@class, "row")][2]//div[contains(@class, '
            '"list-item")][1]')

        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((
                By.XPATH, '{}//div[contains(@class, "form-user-selected")]/div['
                'contains(@class, "secondary")]'.format(qg_1_xpath))))
        self.assertEqual(self.findBy(
            'id', 'id_qg_31-0-key_39').get_attribute('value'), '1055')
        self.assertEqual(self.findBy(
            'id', 'id_qg_31-0-original_key_41').get_attribute('value'), '')

        qg_2_xpath = (
            '//fieldset[contains(@class, "row")][2]//div[contains(@class, '
            '"list-item")][2]')
        self.findByNot(
            'xpath', '{}//div[contains(@class, "form-user-selected")]/div['
            'contains(@class, "secondary")]'.format(qg_2_xpath))
        self.assertEqual(self.findBy(
            'id', 'id_qg_31-1-key_39').get_attribute('value'), '')
        self.assertEqual(self.findBy(
            'id', 'id_qg_31-1-original_key_41').get_attribute(
            'value'), 'Some Person')

        qg_3_xpath = (
            '//fieldset[contains(@class, "row")][2]//div[contains(@class, '
            '"list-item")][3]')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((
                By.XPATH, '{}//div[contains(@class, "form-user-selected")]/div['
                'contains(@class, "secondary")]'.format(qg_3_xpath))))
        self.assertEqual(
            self.findBy('id', 'id_qg_31-2-key_39').get_attribute(
                'value'), '2365')
        self.assertEqual(self.findBy(
            'id', 'id_qg_31-2-original_key_41').get_attribute('value'), '')

        # She submits the step
        self.submit_form_step()

        # She sees all the values are in the overview
        self.checkOnPage('Kurt Gerber')
        self.checkOnPage('Some Person')
        self.checkOnPage('Lukas Vonlanthen')

        # She submits the entire questionnaire
        self.review_action('submit')

        # She sees all the values are in the overview
        self.checkOnPage('Kurt Gerber')
        self.checkOnPage('Some Person')
        self.checkOnPage('Lukas Vonlanthen')

        # She checks the database and sees that 2 users were added
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()
        self.assertEqual(len(questionnaire_users), 3)
        for user_tuple in questionnaire_users:
            self.assertIn(user_tuple[0], ['compiler', 'landuser'])
            self.assertIn(user_tuple[1].id, [1, 1055, 2365])

    @patch.object(WocatAuthenticationMiddleware, 'process_request')
    def test_remove_user(self, mock_process_request, mock_get_user_id,
                         mock_questionnaire_list):

        mock_questionnaire_list.return_value = {}
        mock_process_request.return_value = {}
        # Alice logs in
        self.doLogin()

        # She creates a new Questionnaire with a user attached.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))
        self.rearrangeFormHeader()

        # She does not see a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]')
        self.assertFalse(search_user.is_displayed())

        # She clicks the radio to search for a user
        search_radio = self.findBy(
            'xpath', '//input[@name="form-user-radio" and @value="search"]')
        search_radio.click()

        # She enters a first user by search
        search_user.send_keys('lukas')
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ui-menu-item")))
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Lukas Vonlanthen"]'
        ).click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((
                By.CLASS_NAME, "form-user-search-loading")))

        # She submits the step
        self.submit_form_step()

        # She also enters a name and submits the step
        self.click_edit_section('cat_1')
        self.findBy('id', 'id_qg_1-0-original_key_1').send_keys('Foo')
        self.submit_form_step()

        self.findBy('xpath', '//*[contains(text(), "Foo")]')
        self.findBy('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # Alice edits the questionnaire again
        self.click_edit_section('cat_0')

        # She removes the user from the questionnaire and submits the
        # step
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]/a').click()

        self.submit_form_step()

        # She sees that the user is not listed anymore
        self.findByNot('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # She submits the entire questionnaire and sees that the user is
        # not listed anymore.
        self.review_action('submit')
        self.findByNot('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # Also in the database, the user is not connected to the
        # questionnaire anymore.
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()

        self.assertEqual(len(questionnaire_users), 1)
        for user_tuple in questionnaire_users:
            self.assertIn(user_tuple[0], ['compiler'])
            self.assertIn(user_tuple[1].id, [1])


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class UserTest3(FunctionalTest):

    fixtures = [
        'groups_permissions.json', 'sample_global_key_values.json',
        'sample.json']

    def test_user_questionnaires_no_duplicates(self, mock_get_user_id):

        # Alice logs in
        user = create_new_user()
        user.groups = [
            Group.objects.get(pk=3), Group.objects.get(pk=4)]
        user.save()
        self.doLogin(user=user)

        # She goes directly to the Sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy(
            'xpath', '//input[@name="qg_1-0-original_key_1"]').send_keys(
                'Foo 1')
        self.submit_form_step()
        self.review_action('view')

        details_url = self.browser.current_url

        # She goes to the list of her own questionnaires and sees it.
        self.clickUserMenu(user)
        self.findBy(
            'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
                     'contains(@href, "accounts/questionnaires")]').click()
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 1)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//a['
            'contains(text(), "Foo 1")]')

        # She submits, reviews and publishes the questionnaire
        self.browser.get(details_url)
        self.review_action('submit')
        self.review_action('review')
        self.review_action('publish')

        # Back on the list of her own questionnaires, she sees it only once
        self.clickUserMenu(user)
        self.findBy(
            'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
                     'contains(@href, "accounts/questionnaires")]').click()

        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 1)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//a['
            'contains(text(), "Foo 1")]')


class UserDetailTest(FunctionalTest):

    fixtures = ['global_key_values', 'sample']

    def setUp(self):
        super().setUp()
        self.user = create_new_user()
        self.detail_view_user = create_new_user(
            id=2, email='c@d.com', firstname='abc', lastname='cde'
        )
        self.url = self.live_server_url + reverse(
            'user_details', kwargs={'pk': self.detail_view_user.id}
        )

    def test_user_detail_basic(self):
        # Jay opens the users detail page
        self.browser.get(self.url)

        # The users details are listed
        self.findBy('xpath', '//*[contains(text(), "{}")]'.format(
            self.detail_view_user.firstname)
        )
        self.findBy('xpath', '//*[contains(text(), "{}")]'.format(
            self.detail_view_user.lastname)
        )
        # But not the email address
        self.findByNot('xpath', '//*[contains(text(), "{}")]'.format(
            self.detail_view_user.email)
        )
        # The user is no unccd focal point
        self.findByNot('xpath', '//*[contains(text(), "{}")]'.format(
            'Focal Point')
        )
        # The user has no public questionnaires
        self.findBy('xpath', '//*[contains(text(), "No WOCAT and UNCCD SLM '
                             'practices found.")]')

        # Now jay logs in
        self.doLogin(user=self.user)

        # And can see the users email address
        self.browser.get(self.url)
        self.findBy('xpath', '//*[contains(text(), "{}")]'.format(
            self.detail_view_user.email)
        )

    def test_user_details_full(self):
        # The detail user is now a unccd focal point and hast two public
        # questionnaires
        public = get_valid_questionnaire(user=self.detail_view_user)
        public.status = settings.QUESTIONNAIRE_PUBLIC
        public.save()
        public = get_valid_questionnaire(user=self.detail_view_user)
        public.status = settings.QUESTIONNAIRE_DRAFT
        public.save()
        self.detail_view_user.update(
            email=self.detail_view_user.email,
            usergroups=[{'name': 'UNCCD Focal Point', 'unccd_country': 'CHE'}]
        )
        self.browser.get(self.url)

        # The public questionnaire is now listed.
        self.findBy('xpath', '(//article[contains(@class, "tech-item")])[1]//*'
                             '[contains(text(), "No description available.")]')

        # The list is exactly one element long, the draft is not visible
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 1)

        # And finally, the unccd focal point country switzerland is listed.
        self.findBy('xpath', '//*[contains(text(), "focal point")]')
        self.findBy('xpath', '//div[contains(@class, "user-unccd-focal-point")]')
        self.findBy('xpath', '//a[text()="Switzerland"]')

# @override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
# @patch.object(Typo3Client, 'get_user_id')
# class UserTestFixtures(FunctionalTest):
#
#     fixtures = [
#         'sample_global_key_values.json', 'sample.json',
#         'sample_questionnaires_users.json']
#
#     @patch('accounts.views.get_user_information')
#     def test_update_user(self, mock_get_user_information, mock_get_user_id):
#
#         # Alice logs in
#         self.doLogin()
#
#         # She goes to a questionnaire with a user attached to it
#         self.browser.get(self.live_server_url + reverse(
#             route_questionnaire_details, args=['sample_1']))
#
#         # In the questionnaire details, she sees the user name and also
#         # the user which is not registered.
#         self.findBy('xpath', '//*[contains(text(), "Faz Taz")]')
#         self.findBy('xpath', '//*[contains(text(), "Some other person")]')
#
#         # In the backend, the username changes
#         questionnaire = Questionnaire.objects.first()
#         questionnaire_users = questionnaire.get_users()
#         self.assertEqual(len(questionnaire_users), 2)
#         user = questionnaire_users[1][1]
#         user.lastname = 'Foo'
#         user.save()
#
#         # She refreshes the questionnaire details and
#         # sees that nothing changed
#         self.browser.refresh()
#         self.findBy('xpath', '//*[contains(text(), "Faz Taz")]')
#         self.findBy('xpath', '//*[contains(text(), "Some other person")]')
#
#         mock_get_user_information.return_value = {
#             'last_name': 'Wayne',
#             'first_name': 'Bruce',
#         }
#
#         # She goes to the detail page of the user and sees the name is
#         # updated if the page is loaded.
#         self.browser.get(
#             self.live_server_url + reverse(accounts_route_user, args=[102]))
#         self.findBy('xpath', '//*[contains(text(), "Bruce")]')
#         self.findBy('xpath', '//*[contains(text(), "Wayne")]')
#
#         # She goes back to the details of the questionnaire and sees the
#         # name is now updated. The non-registered user is still there.
#         self.browser.get(self.live_server_url + reverse(
#             route_questionnaire_details, args=['sample_1']))
#         self.findBy('xpath', '//*[contains(text(), "Bruce Wayne")]')
#         self.findBy('xpath', '//*[contains(text(), "Some other person")]')
