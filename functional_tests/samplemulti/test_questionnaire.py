from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from functional_tests.base import FunctionalTest
from unittest.mock import patch

from accounts.client import Typo3Client
from samplemulti.tests.test_views import (
    route_home,
    route_questionnaire_new_step,
    get_category_count,
    get_categories,
)

TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class QuestionnaireTest(FunctionalTest):

    fixtures = ['global_key_values.json', 'samplemulti.json']

    def test_questionnaire_is_available(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to the SAMPLEMULTI app
        self.browser.get(self.live_server_url + reverse(route_home))

        # She sees a link to enter a new questionnaire and clicks it
        self.findBy(
            'xpath', '//a[@href="/en/samplemulti/edit/new/" and '
            'contains(@class, "button")]'
        ).click()

        # She is taken to the form and sees the steps
        progress_indicators = self.findManyBy(
            'xpath', '//div[@class="tech-section-progress progress"]')
        self.assertEqual(len(progress_indicators), get_category_count())

        # She goes to the first step and sees the link works.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step, kwargs={
                'identifier': 'new', 'step': get_categories()[0][0]}))

        self.findBy('id', 'button-submit').click()
        progress_indicators = self.findManyBy(
            'xpath', '//div[@class="tech-section-progress progress"]')
        self.assertEqual(len(progress_indicators), get_category_count())

    def test_questionnaire_can_be_entered(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes directly to the first step of the form
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step,
            kwargs={'identifier': 'new', 'step': 'mcat_1'}))

        # She enters some values for Key 1
        self.findBy('name', 'mqg_01-0-original_mkey_01').send_keys('Foo')

        # She submits the form and sees the values are in the overview
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"MKey 1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')

        # She submits the form and sees the values are in the details
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//*[text()[contains(.,"MKey 1")]]')
        self.findBy('xpath', '//*[text()[contains(.,"Foo")]]')
