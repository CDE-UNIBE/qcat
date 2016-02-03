from django.core.urlresolvers import reverse
from unittest.mock import patch

from accounts.client import Typo3Client
from functional_tests.base import FunctionalTest
from unccd.tests.test_views import route_home


@patch.object(Typo3Client, 'get_user_id')
class QuestionnaireTest(FunctionalTest):

    fixtures = ['global_key_values.json', 'unccd.json']

    def test_questionnaire_is_available(self, mock_get_user_id):

        # Alice logs in
        self.doLogin()

        # She goes to the UNCCD app
        self.browser.get(self.live_server_url + reverse(route_home))

        # She does not see a link to enter a new questionnaire and clicks it
        self.findByNot(
            'xpath',
            '//a[@href="/en/unccd/edit/new/" and contains(@class, "button")]'
        )

        # # She is taken to the form and sees the steps
        # progress_indicators = self.findManyBy(
        #     'xpath', '//div[@class="tech-section-progress progress"]')
        # self.assertEqual(len(progress_indicators), get_category_count())

        # # She goes to the first step and sees the link works.
        # self.browser.get(self.live_server_url + reverse(
        #     route_questionnaire_new_step, kwargs={
        #         'identifier': 'new', 'step': get_categories()[0][0]}))

        # self.findBy('id', 'button-submit').click()
        # progress_indicators = self.findManyBy(
        #     'xpath', '//div[@class="tech-section-progress progress"]')
        # self.assertEqual(len(progress_indicators), get_category_count())
