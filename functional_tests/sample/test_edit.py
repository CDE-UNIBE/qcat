from django.core.urlresolvers import reverse
from unittest.mock import patch

from accounts.client import Typo3Client
from accounts.models import User
from functional_tests.base import FunctionalTest
from questionnaire.models import Questionnaire
from sample.tests.test_views import (
    get_position_of_category,
    route_home,
    route_questionnaire_details,
    route_questionnaire_new,
)

from django.contrib.auth.models import Group
from accounts.tests.test_models import create_new_user
from nose.plugins.attrib import attr  # noqa
# @attr('foo')

cat_1_position = get_position_of_category('cat_1', start0=True)


def has_old_version_step(browser):
    browser.findBy(
        'xpath', '//p[contains(text(), "There is an old version with changes '
        'in this section.")]')


def has_no_old_version_step(browser):
    browser.findByNot(
        'xpath', '//p[contains(text(), "There is an old version with changes '
        'in this section.")]')


def has_old_version_overview(browser):
    browser.findBy(
        'xpath', '//p[contains(text(), "There is an old version which is '
        'different than the current one.")]')


def has_no_old_version_overview(browser):
    browser.findByNot(
        'xpath', '//p[contains(text(), "There is an old version which is '
        'different than the current one.")]')


@patch.object(Typo3Client, 'get_user_id')
class EditTest(FunctionalTest):

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
        (public by user 101 [compiler] and 102 [editor])

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

    # def test_concurrent_edits(self):

    #     user_alice = User.objects.get(pk=101)
    #     user_bob = User.objects.get(pk=102)

    #     # Alice logs in
    #     self.doLogin(user=user_alice)

    #     # She starts editing a new questionnaire
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new))
    #     self.findBy(
    #         'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
    #             cat_1_position+1)).click()
    #     self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
    #     self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
    #     self.findBy('id', 'button-submit').click()

    #     self.findBy('xpath', '//div[contains(@class, "success")]')

    #     # She sees the changes saved in the session
    #     self.findBy('xpath', '//article//*[text()="Foo"]')

    #     # Bob logs in
    #     self.doLogin(user=user_bob)

    #     # He also starts editing a new questionnaire.
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new))

    #     # He does not see the changes saved by Alice
    #     self.findByNot('xpath', '//article//*[text()="Foo"]')

    #     # He enters his own data
    #     self.findBy(
    #         'xpath', '(//a[contains(@href, "edit/new/cat")])[{}]'.format(
    #             cat_1_position+1)).click()
    #     self.findBy('name', 'qg_1-0-original_key_1').send_keys('Faz')
    #     self.findBy('name', 'qg_1-0-original_key_3').send_keys('Taz')
    #     self.findBy('id', 'button-submit').click()
    #     self.findBy('xpath', '//div[contains(@class, "success")]')

    #     # He sees the changes saved in the session
    #     self.findByNot('xpath', '//article//*[text()="Foo"]')
    #     self.findBy('xpath', '//article//*[text()="Faz"]')

    #     # Again, Alice logs in
    #     self.doLogin(user=user_alice)

    #     # She goes to the questionnaire form and sees her edits from before
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new))
    #     self.findBy('xpath', '//article//*[text()="Foo"]')
    #     self.findByNot('xpath', '//article//*[text()="Faz"]')

    #     # She saves the questionnaire and sees the values were stored
    #     self.findBy('id', 'button-submit').click()
    #     self.findBy('xpath', '//div[contains(@class, "success")]')
    #     self.findBy('xpath', '//article//*[text()="Foo"]')
    #     self.findByNot('xpath', '//article//*[text()="Faz"]')

    #     # She starts a new form and sees no values are there
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new))
    #     self.findByNot('xpath', '//article//*[text()="Foo"]')
    #     self.findByNot('xpath', '//article//*[text()="Faz"]')

    #     # Bob logs in again
    #     self.doLogin(user=user_bob)

    #     # He goes to the questionnaire form and sees his edits from before
    #     self.browser.get(self.live_server_url + reverse(
    #         route_questionnaire_new))
    #     self.findByNot('xpath', '//article//*[text()="Foo"]')
    #     self.findBy('xpath', '//article//*[text()="Faz"]')

    def test_creation_date_does_not_change(self, mock_get_user_id):

        # Alice logs in
        user = User.objects.get(pk=102)
        self.doLogin(user=user)

        # She goes to the details of an existing questionnaire and takes
        # note of the creation and update dates
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_3'}))
        dates = self.findManyBy(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/time')
        self.assertEqual(len(dates), 2)
        creation_date = dates[0].text
        update_date = dates[1].text

        # She edits the questionnaire
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.findManyBy(
            'xpath',
            '//a[contains(@href, "edit/sample_3/cat")]')[
                cat_1_position].click()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys(' (changed)')

        # She submits the questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees the changes were submitted
        self.findBy('xpath', '//*[text()[contains(.," (changed)")]]')

        # She notices that the creation date did not change while the
        # update date changed.
        dates = self.findManyBy(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/time')
        self.assertEqual(len(dates), 2)
        self.assertEqual(creation_date, dates[0].text)
        self.assertTrue(update_date != dates[1].text)

        # Alice logs in as a different user
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She also opens a draft version of a questionnaire and takes
        # note of the creation and update dates
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        dates = self.findManyBy(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/time')
        self.assertEqual(len(dates), 2)
        creation_date = dates[0].text
        update_date = dates[1].text

        # She makes an edit
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.findManyBy(
            'xpath',
            '//a[contains(@href, "edit/sample_1/cat")]')[
                cat_1_position].click()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys(' (changed)')

        # She submits the questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees the changes were submitted
        self.findBy('xpath', '//*[text()[contains(.," (changed)")]]')

        # She notices that the creation date did not change while the
        # update date changed.
        dates = self.findManyBy(
            'xpath', '//ul[contains(@class, "tech-output-infos")]/li/time')
        self.assertEqual(len(dates), 2)
        self.assertEqual(creation_date, dates[0].text)
        self.assertTrue(update_date != dates[1].text)

    def test_edit_draft(self, mock_get_user_id):

        code = 'sample_1'

        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She goes to the detail page of a "draft" Questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': code}))
        self.assertIn(code, self.browser.current_url)

        self.findBy('xpath', '//*[text()[contains(.,"Foo 1")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"asdf")]]')

        # She edits the Questionnaire and sees that the URL contains the
        # code of the questionnaire
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.assertIn(code, self.browser.current_url)

        # She edits a category and sees that the URL still contains the
        # code of the Questionnaire
        self.findManyBy(
            'xpath',
            '//a[contains(@href, "edit/{}/cat")]'.format(code))[
                cat_1_position].click()
        self.assertIn(code, self.browser.current_url)

        # She makes some changes and submits the category
        key_1 = self.findBy('name', 'qg_1-0-original_key_1')
        key_1.clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('asdf')
        self.findBy('id', 'button-submit').click()

        # She is back on the overview page and sees that the URL still
        # contains the code of the Questionnaire
        self.assertIn(code, self.browser.current_url)

        # She submits the Questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that no new code was created.
        self.assertIn(code, self.browser.current_url)

        # She sees that the value of Key 1 was updated
        self.findByNot('xpath', '//*[text()[contains(.,"Foo 1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"asdf")]]')

        # Also there was no additional version created in the database
        self.assertEqual(Questionnaire.objects.count(), 10)

    def test_edit_public(self, mock_get_user_id):

        code = 'sample_3'

        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She goes to the detail page of a "public" Questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': code}))
        self.assertIn(code, self.browser.current_url)

        self.findBy('xpath', '//*[text()[contains(.,"Foo 3")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"asdf")]]')

        # She edits the Questionnaire and sees that the URL contains the
        # code of the Questionnaire
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.assertIn(code, self.browser.current_url)

        #  She edits a category and sees that the URL still contains the
        # code of the Questionnaire
        self.findManyBy(
            'xpath',
            '//a[contains(@href, "edit/{}/cat")]'.format(code))[
                cat_1_position].click()
        self.assertIn(code, self.browser.current_url)

        # She makes some changes and submits the category
        key_1 = self.findBy('name', 'qg_1-0-original_key_1')
        key_1.clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('asdf')
        self.findBy('id', 'button-submit').click()

        # She is back on the overview page and sees that the URL still
        # contains the code of the Questionnaire
        self.assertIn(code, self.browser.current_url)

        # She submits the Questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that no new code was created.
        self.assertIn(code, self.browser.current_url)

        # She sees that the value of Key 1 was updated
        self.findByNot('xpath', '//*[text()[contains(.,"Foo 3")]]')
        self.findBy('xpath', '//*[text()[contains(.,"asdf")]]')

        # Also there was an additional version created in the database
        self.assertEqual(Questionnaire.objects.count(), 11)

        # The newly created version has the same code
        self.assertEqual(Questionnaire.objects.filter(code=code).count(), 2)

        # She goes to the home page and sees the list of last updates
        # where sample_3 appears only once.
        self.browser.get(self.live_server_url + reverse(route_home))

        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 3)

        self.findBy(
            'xpath', '//a[contains(text(), "asdf")]', base=list_entries[0])
        self.findBy(
            'xpath', '//a[contains(text(), "Foo 1")]', base=list_entries[1])
        self.findBy(
            'xpath', '//a[contains(text(), "Foo 5")]', base=list_entries[2])

        # She clicks the first entry and sees that she is taken to the
        # details page of the latest (pending) version.
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "asdf")]').click()
        self.checkOnPage('asdf')

    def test_edit_questionnaire(self, mock_get_user_id):

        user = create_new_user(id=6, email='mod@bar.com')
        user.groups = [Group.objects.get(pk=3), Group.objects.get(pk=4)]
        user.save()

        # Alice logs in
        self.doLogin(user=user)

        # She enters a Questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        edit_buttons = self.findManyBy(
            'xpath', '//a[contains(@href, "edit/new/cat")]')
        edit_buttons[cat_1_position].click()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She saves it as draft
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She submits it for review
        self.findBy('xpath', '//input[@name="submit"]').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She reviews it
        self.findBy('xpath', '//input[@name="review"]').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She publishes it
        self.findBy('xpath', '//input[@name="publish"]').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees it is public and visible
        self.findBy('xpath', '//p[text()="Foo"]')
        self.findBy('xpath', '//p[text()="Bar"]')

        url = self.browser.current_url

        # She edits it
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.findBy(
            'xpath', '(//a[contains(text(), "Edit this section")])[2]').click()

        # She changes some values
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('asdf')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She saves it as draft
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She is taken to the overview page where she sees the latest
        # (pending) changes of the draft

        self.assertEqual(url, self.browser.current_url)

        self.findBy('xpath', '//p[text()="Bar"]')
        self.findByNot('xpath', '//p[text()="Foo"]')
        self.findBy('xpath', '//p[text()="asdf"]')

    def test_show_message_of_changed_versions(self, mock_get_user_id):

        user = create_new_user(id=6, email='mod@bar.com')
        user.groups = [Group.objects.get(pk=3), Group.objects.get(pk=4)]
        user.save()

        initial_db_count = Questionnaire.objects.count()

        # Alice logs in
        self.doLogin(user=user)

        # She enters a Questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))

        # She sees there is no message of an old version
        has_no_old_version_overview(self)

        edit_buttons = self.findManyBy(
            'xpath', '//a[contains(@href, "edit/new/cat")]')
        edit_buttons[cat_1_position].click()

        has_no_old_version_step(self)
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees there is no message of an old version
        has_no_old_version_overview(self)

        # She saves it as draft
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # In the database, there is only one Questionnaire
        self.assertEqual(Questionnaire.objects.count(), initial_db_count + 1)

        # She sees there is no message of an old version
        has_no_old_version_overview(self)

        # She edits it
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()

        # She sees there is no message of an old version
        has_no_old_version_overview(self)

        self.findBy(
            'xpath', '(//a[contains(text(), "Edit this section")])[2]').click()

        # She sees there is no message of an old version
        has_no_old_version_step(self)

        # She changes some values
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('asdf')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees there is a message of an old version
        has_old_version_overview(self)

        # She edits the step again and sees there is now a message of changes
        self.findBy(
            'xpath', '(//a[contains(text(), "Edit this section")])[2]').click()
        has_old_version_step(self)

        # She reverts the changes made before and submits the step
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees there is no change message anymore.
        has_no_old_version_overview(self)

        # She goes back to the step and sees there is no change message
        # there either.
        self.findBy(
            'xpath', '(//a[contains(text(), "Edit this section")])[2]').click()
        has_no_old_version_step(self)

        # She makes some new changes, submits the step and sees the
        # message is back.
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('asdf')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        has_old_version_overview(self)

        # She saves it as draft
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # In the database, there is only one Questionnaire
        self.assertEqual(Questionnaire.objects.count(), initial_db_count + 1)

        # She sees there is no message of an old version
        has_no_old_version_overview(self)

        # She edits it again and sees there is a message about the changes
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        has_old_version_overview(self)

        # She edits a step and sees the message about changes there as well
        self.findBy(
            'xpath', '(//a[contains(text(), "Edit this section")])[2]').click()
        has_old_version_step(self)
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She saves it as draft and submits it for review
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # There is no message about changes
        has_no_old_version_overview(self)

        # She is moderator and sets the questionnaire public, there is
        # no message about changes
        self.findBy('id', 'button-review').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('id', 'button-publish').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        has_no_old_version_overview(self)

        # In the database, there is only one Questionnaire
        self.assertEqual(Questionnaire.objects.count(), initial_db_count + 1)

        # She edits it again and sees there is no change message
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        has_no_old_version_overview(self)
