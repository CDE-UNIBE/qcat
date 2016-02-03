from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from unittest.mock import patch

from accounts.client import Typo3Client
from accounts.tests.test_models import create_new_user
from functional_tests.base import FunctionalTest
from sample.tests.test_views import (
    get_position_of_category,
    route_questionnaire_new_step as sample_route_questionnaire_new_step,
    route_questionnaire_new as sample_route_questionnaire_new,
    route_home as sample_route_home,
)
from unccd.tests.test_views import (
    route_questionnaire_new_step as unccd_route_questionnaire_new_step,
)


from nose.plugins.attrib import attr  # noqa
# @attr('foo')

TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@patch.object(Typo3Client, 'get_user_id')
@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class SessionTest(FunctionalTest):

    fixtures = [
        'global_key_values.json', 'sample.json', 'unccd.json']

    # def test_stores_session_dictionary_correctly(self):

    #     # Alice logs in
    #     self.doLogin()

    #     # She goes to a step of the questionnaire
    #     self.browser.get(self.live_server_url + reverse(
    #         sample_route_questionnaire_new_step,
    #         kwargs={'identifier': 'new', 'step': 'cat_1'}))

    #     # She enters something as first key
    #     key_1 = self.findBy('name', 'qg_1-0-original_key_1')
    #     self.assertEqual(key_1.text, '')
    #     key_1.send_keys('Foo')

    #     self.findBy('id', 'button-submit').click()

    #     self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
    #     session_data = get_session_questionnaire('sample', None)
    #     self.assertEqual(
    #         session_data.get('questionnaire'),
    #         {'qg_1': [{'key_1': {'en': 'Foo'}}]})
    #     self.assertEqual(session_data.get('links'), {})

    #     # self.assertEqual(self.browser.current_url, 'foo')
    #     self.findBy('id', 'button-submit').click()

    def test_sessions_separated_by_configuration(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to a step of the sample questionnaire
        self.browser.get(self.live_server_url + reverse(
            sample_route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))

        # She enters something as first key
        key_1 = self.findBy('name', 'qg_1-0-original_key_1')
        self.assertEqual(key_1.text, '')
        key_1.send_keys('Foo')

        # She submits the form and sees the value is stored in the
        # session and displayed in the overview
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')

        # She goes to a step of the unccd questionnaire
        self.browser.get(self.live_server_url + reverse(
            unccd_route_questionnaire_new_step,
            kwargs={
                'identifier': 'new', 'step': 'unccd_0_general_information'}))

        # She enters something as first key
        key_1 = self.findBy('name', 'qg_name-0-original_name')
        self.assertEqual(key_1.text, '')
        key_1.send_keys('Bar')

        # She submits the form and sees the value is stored in the
        # session and displayed in the overview
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Foo")]]')

        # She submits the unccd questionnaire and sees only the unccd value
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Foo")]]')

        # She goes back to the sample questionnaire and sees the value
        # in the session is still there
        self.browser.get(self.live_server_url + reverse(
            sample_route_questionnaire_new))
        self.findBy('xpath', '//article//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Bar")]]')

        # She submits the questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//article//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//article//*[text()[contains(.,"Bar")]]')


@patch.object(Typo3Client, 'get_user_id')
class SessionTest2(FunctionalTest):

    fixtures = [
        'groups_permissions.json', 'sample_global_key_values.json',
        'sample.json']

    def test_sessions_separated_by_questionnaire(self, mock_get_user_id):

        cat_1_position = get_position_of_category('cat_1')

        user_moderator = create_new_user(id=2, email='foo@bar.com')
        user_moderator.groups = [
            Group.objects.get(pk=3), Group.objects.get(pk=4)]
        user_moderator.save()

        # Alice logs in
        self.doLogin(user=user_moderator)

        # She enters a new Questionnaire
        self.browser.get(self.live_server_url + reverse(
            sample_route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Bar')
        self.findBy('id', 'button-submit').click()

        # She saves the Questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She submits the Questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She publishes the Questionnaire
        self.findBy('id', 'button-review').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('id', 'button-publish').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She decides to edit the Questionnaire again
        self.findBy('xpath', '//a[contains(@href, "/sample/edit/")]').click()

        # The values of Questionnaire 1 are not stored in the session.
        # She decides to start entering a new Questionnaire and sees
        # that there are no values available yet
        self.browser.get(
            self.live_server_url + reverse(sample_route_questionnaire_new))
        self.findByNot('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')

        # She enters some values
        self.browser.get(self.live_server_url + reverse(
            sample_route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'cat_1'}))
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Faz')
        self.findBy('name', 'qg_1-0-original_key_3').send_keys('Taz')
        self.findBy('id', 'button-submit').click()

        # She sees the values were stored in the session
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Taz")]]')

        # She goes back to edit the first Questionnaire
        self.browser.get(self.live_server_url + reverse(sample_route_home))
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo")]').click()
        self.findBy('xpath', '//a[contains(@href, "/sample/edit/")]').click()

        # She sees the previous values are still there, but not the new ones.
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Faz")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Taz")]]')

        # She goes back to the new form and sees the new values are still there
        self.browser.get(
            self.live_server_url + reverse(sample_route_questionnaire_new))
        self.findByNot('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Taz")]]')

        # She once again goes to the first Questionnaires, makes changes
        # and saves the Questionnaire
        self.browser.get(self.live_server_url + reverse(sample_route_home))
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//h1/a['
            'contains(text(), "Foo")]').click()
        self.findBy('xpath', '//a[contains(@href, "/sample/edit/")]').click()

        self.findBy(
            'xpath', '(//a[contains(@href, "/sample/edit/")])[{}]'.format(
                cat_1_position)).click()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys(' asdf')
        self.findBy('id', 'button-submit').click()

        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo asdf")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Faz")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Taz")]]')

        # Back in the new form, the new values are still there
        self.browser.get(
            self.live_server_url + reverse(sample_route_questionnaire_new))
        self.findByNot('xpath', '//*[text()[contains(.,"Foo")]]')
        self.findByNot('xpath', '//*[text()[contains(.,"Bar")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Faz")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Taz")]]')
