from django.core.urlresolvers import reverse
from unittest.mock import patch

from accounts.client import Typo3Client
from functional_tests.base import FunctionalTest
from technologies.tests.test_views import (
    route_questionnaire_new_step,
    get_category_count,
    get_categories,
)
from wocat.tests.test_views import route_home


@patch('wocat.views.generic_questionnaire_list')
@patch.object(Typo3Client, 'get_user_id')
class QuestionnaireTest(FunctionalTest):

    fixtures = ['global_key_values.json', 'technologies.json']

    def test_questionnaire_is_available(self, mock_get_user_id,
                                        mock_questionnaire_list):

        mock_questionnaire_list.return_value = {}
        # Alice logs in
        self.doLogin()

        # She goes to the landing page
        self.browser.get(self.live_server_url + reverse(route_home))

        # She clicks "Add SLM data" in the top menu
        self.findBy('xpath', '//section[contains(@class, "top-bar-section")]//'
                             'a[contains(@href, "/wocat/add")]').click()

        # She is taken to a page where she can click "add new Tech"
        self.findBy(
            'xpath', '//div[contains(@class, "card")]//a[contains('
                     '@href, "/technologies/edit/new")]').click()

        # She is taken to the form and sees the steps
        progress_indicators = self.findManyBy(
            'xpath', '//div[@class="tech-section-progress"]')

        self.assertEqual(len(progress_indicators), get_category_count())

        # She sees that all the categories are there with their correct name
        # Except the first one which is not displayed in the header template
        for category in [c[1] for c in get_categories()][1:]:
            self.findBy('xpath', '//h2[contains(text(), "' + category + '")]')

        # She goes to the first step and sees the link works.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_step, kwargs={
                'identifier': 'new', 'step': get_categories()[0][0]}))

        # The script to set the focus point for the image is loaded, and the
        # hidden field is in the DOM.
        self.browser.execute_script("return $.addFocusPoint();")
        self.findBy('id', 'id_qg_image-0-image_target')

        self.findBy('id', 'button-submit').click()
        progress_indicators = self.findManyBy(
            'xpath', '//div[@class="tech-section-progress"]')
        self.assertEqual(len(progress_indicators), get_category_count())
