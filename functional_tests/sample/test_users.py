from django.core.urlresolvers import reverse
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
    route_questionnaire_details,
)
from accounts.tests.test_views import accounts_route_user


from nose.plugins.attrib import attr  # noqa
# @attr('foo')

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
        self.findBy(
            'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
            'contains(@href, "accounts/101/questionnaires")]').click()

        # She sees here Questionnaires are listed, even those with
        # status draft or submitted
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 7)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo 1")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
            'contains(text(), "Foo 3")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[3]//h1/a['
            'contains(text(), "Foo 4")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[4]//h1/a['
            'contains(text(), "Foo 5")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[5]//h1/a['
            'contains(text(), "Foo 7")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[6]//h1/a['
            'contains(text(), "Foo 8")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[7]//h1/a['
            'contains(text(), "Foo 9")]')

        # She sees a customized title of the list
        self.findBy('xpath', '//h2[contains(text(), "Your SLM practices")]')
        self.findByNot(
            'xpath', '//h2[contains(text(), "SLM practices by Foo Bar")]')

        # She goes to the questionnaire page of Bob and sees the
        # Questionnaires of Bob but only the "public" ones.
        self.browser.get(self.live_server_url + reverse(
            accounts_route_questionnaires, kwargs={'user_id': 102}))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo 3")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
            'contains(text(), "Foo 8")]')

        # She logs out and sees the link in the menu is no longer visible.
        self.doLogout()
        self.findByNot(
            'xpath', '//li[contains(@class, "has-dropdown")]/ul/li/a['
            'contains(@href, "accounts/101/questionnaires")]')

        # On her Questionnaire page only the "public" Questionnaires are
        # visible.
        self.browser.get(self.live_server_url + reverse(
            accounts_route_questionnaires, kwargs={'user_id': 101}))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo 3")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
            'contains(text(), "Foo 5")]')

        # Bob logs in and goes to his Questionnaire page. He sees all
        # versions of his Questionnaires.
        self.doLogin(user=user_bob)
        self.browser.get(self.live_server_url + reverse(
            accounts_route_questionnaires, kwargs={'user_id': 102}))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 3)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo 2")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
            'contains(text(), "Foo 3")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[3]//h1/a['
            'contains(text(), "Foo 8")]')

        # He goes to the Questionnaire page of Alice and only sees the
        # "public" Questionnaires.
        self.browser.get(self.live_server_url + reverse(
            accounts_route_questionnaires, kwargs={'user_id': 101}))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 3)
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo 3")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//h1/a['
            'contains(text(), "Foo 5")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[3]//h1/a['
            'contains(text(), "Foo 8")]')

        # He sees that the customized title of the list now changed.
        self.findByNot(
            'xpath', '//h2[contains(text(), "Your SLM practices")]')
        self.findBy(
            'xpath', '//h2[contains(text(), "SLM practices by Foo Bar")]')

        # He goes to the Questionnaire page of Chris and sees no
        # "public" Questionnaires with an appropriate message.
        self.browser.get(self.live_server_url + reverse(
            accounts_route_questionnaires, kwargs={'user_id': 103}))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 0)
        self.findBy(
            'xpath', '//p[@class="questionnaire-list-empty" and contains('
            'text(), "No WOCAT and UNCCD SLM practices found.")]')


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class UserTest2(FunctionalTest):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def test_add_user(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]'
            '[1]')

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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees the name is in the overview
        self.checkOnPage('Kurt Gerber')

        # She goes back to the form
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees the user is selected, loading and search fields are
        # not visible
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Lukas Vonlanthen')

        # She submits the entire questionnaire and sees the name is there
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Lukas Vonlanthen')

        # She checks the database to make sure the user was added.
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()
        self.assertEqual(len(questionnaire_users), 2)
        for user_tuple in questionnaire_users:
            self.assertIn(user_tuple[0], ['compiler', 'landuser'])
            self.assertIn(user_tuple[1].id, [1, 2365])

    def test_add_new_person(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]'
            '[1]')
        search_tab = self.findBy(
            'xpath', '//li[contains(@class ,"tab-title") and contains('
            '@class, "active")]/a[contains(@class, "show-tab-select")]')

        # She also sees that there is a tab to add new persons, which is
        # not active.
        new_tab = self.findBy(
            'xpath', '//li[contains(@class ,"tab-title") and not('
            'contains(@class, "active"))]/a[contains(@class, '
            '"show-tab-create")]')
        new_name = self.findBy('id', 'id_qg_31-0-original_key_41')
        self.assertFalse(new_name.is_displayed())

        # She clicks the tab and sees that the input field is visible
        new_tab.click()
        self.assertTrue(new_name.is_displayed())

        # She decides to search for a user first
        search_tab.click()
        self.assertFalse(new_name.is_displayed())

        # There is no loading indicator
        loading_indicator = self.findBy(
            'xpath', '//div[contains(@class, "form-user-search-loading")][1]')
        self.assertFalse(loading_indicator.is_displayed())

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
        new_tab.click()
        new_name.send_keys('New Person')
        self.assertEqual(new_name.get_attribute('value'), 'New Person')

        # She is having second thoughts and decides to search for a
        # person once again
        search_tab.click()
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

        # She goes back to the select tab and sees that the values she
        # entered previously are gone now
        new_tab.click()
        self.assertEqual(new_name.get_attribute('value'), '')

        # She enters a new name
        new_name.send_keys('Other New Person')
        self.findBy('xpath', '//html').click()  # Lose focus
        self.assertTrue(new_name.is_displayed())

        # She goes back to the other tab and sees the selected user is gone
        search_tab.click()
        self.findByNot(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]')

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees the new person was submitted correctly
        self.checkOnPage('Other New Person')
        self.findByNot('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # She goes back to the form
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees the tab with the new user details is shown
        new_name = self.findBy('id', 'id_qg_31-0-original_key_41')
        self.assertTrue(new_name.is_displayed())
        self.assertEqual(new_name.get_attribute('value'), 'Other New Person')

        self.findByNot(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]')

        # She changes the value of the new person
        new_name.clear()
        new_name.send_keys('Person A')

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Person A')

        # She submits the entire questionnaire and sees the name is there
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.checkOnPage('Person A')

        # She checks the database to make sure no additional user was added.
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()
        self.assertEqual(len(questionnaire_users), 1)
        self.assertEqual(questionnaire_users[0][0], 'compiler')
        self.assertEqual(questionnaire_users[0][1].id, 1)

    def test_add_multiple_users_persons(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]'
            '[1]')

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

        # She sees that the second group shows the search field by
        # default, no user is selected
        qg_2_xpath = (
            '//fieldset[contains(@class, "row")][2]//div[contains(@class, '
            '"list-item")][2]')
        search_user_2 = self.findBy(
            'xpath', '{}//input[contains(@class, "user-search-field")]'.format(
                qg_2_xpath))
        self.assertTrue(search_user_2.is_displayed())

        self.findByNot(
            'xpath', '{}//div[contains(@class, "form-user-selected")]/div['
            'contains(@class, "secondary")]'.format(qg_2_xpath))

        # She adds the second user as a non-registered person
        self.findBy(
            'xpath', '{}//a[contains(@class, "show-tab-create")]'.format(
                qg_2_xpath)).click()
        self.findBy('id', 'id_qg_31-1-original_key_41').send_keys(
            'Some Person')

        # She adds a third person
        self.findBy(
            'xpath', '//fieldset[contains(@class, "row")][2]//a['
            'contains(@class, "link") and @data-questiongroup-keyword='
            '"qg_31"]').click()

        # She sees that the third group shows the search field by
        # default, no user is selected
        qg_3_xpath = (
            '//fieldset[contains(@class, "row")][2]//div[contains(@class, '
            '"list-item")][3]')
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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees all the values are in the overview
        self.checkOnPage('Kurt Gerber')
        self.checkOnPage('Some Person')
        self.checkOnPage('Lukas Vonlanthen')

        # She goes back to the form
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees that the form was populated correctly
        qg_1_xpath = (
            '//fieldset[contains(@class, "row")][2]//div[contains(@class, '
            '"list-item")][1]')
        self.findBy(
            'xpath', '{}//div[contains(@class, "form-user-selected")]/div['
            'contains(@class, "secondary")]'.format(qg_1_xpath))
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
        self.findBy(
            'xpath', '{}//div[contains(@class, "form-user-selected")]/div['
            'contains(@class, "secondary")]'.format(qg_3_xpath))
        self.assertEqual(
            self.findBy('id', 'id_qg_31-2-key_39').get_attribute(
                'value'), '2365')
        self.assertEqual(self.findBy(
            'id', 'id_qg_31-2-original_key_41').get_attribute('value'), '')

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees all the values are in the overview
        self.checkOnPage('Kurt Gerber')
        self.checkOnPage('Some Person')
        self.checkOnPage('Lukas Vonlanthen')

        # She submits the entire questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

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

    def test_remove_user(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She creates a new Questionnaire with a user attached.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_0'}))

        # She sees a field to search for users
        search_user = self.findBy(
            'xpath', '//input[contains(@class, "user-search-field")]'
            '[1]')

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
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She also enters a name and submits the step
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy('id', 'id_qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She submits the entire questionnaire and sees the user was
        # added
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[contains(text(), "Foo")]')
        self.findBy('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # Alice edits the questionnaire again
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'sample_0', 'step': 'cat_0'}))

        # She removes the user from the questionnaire and submits the
        # step
        self.findBy(
            'xpath', '//div[contains(@class, "alert-box") and contains(text(),'
            '"Lukas Vonlanthen")]/a').click()

        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that the user is not listed anymore
        self.findByNot('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # She submits the entire questionnaire and sees that the user is
        # not listed anymore.
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findByNot('xpath', '//*[contains(text(), "Lukas Vonlanthen")]')

        # Also in the database, the user is not connected to the
        # questionnaire anymore.
        questionnaire = Questionnaire.objects.first()
        questionnaire_users = questionnaire.get_users()

        self.assertEqual(len(questionnaire_users), 1)
        for user_tuple in questionnaire_users:
            self.assertIn(user_tuple[0], ['compiler'])
            self.assertIn(user_tuple[1].id, [1])


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
#         # She refreshes the questionnaire details and sees that nothing changed
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
