import logging
from unittest.mock import patch

from django.core.urlresolvers import reverse

from functional_tests.base import FunctionalTest
from summary.views import SummaryPDFCreateView


logging.disable(logging.CRITICAL)


class SummaryTest(FunctionalTest):

    fixtures = ['global_key_values.json', 'sample.json',
                'sample_questionnaires.json']

    def setUp(self):
        super().setUp()
        self.url = '{base}{summary_url}'.format(
            base=self.live_server_url,
            summary_url=reverse('questionnaire_summary', kwargs={'id': 1})
        )
        self.data_title_mock = {
            'title': {
                'partials': {
                    'title': 'Success story',
                    'country': 'Wonderland',
                    'local_name': 'The Rabbit Hole',
                }
            }
        }

    def test_summary_no_configured_summary(self):
        # The summary page is visited, but no configuration is stored for the
        # sample summary
        response = self.browser.get(self.url)
        self.assertIsNone(response)

    # opening files seems tricky. as almost the same is tested with the
    # ?as=html, not much effort was put into this test.
    # @patch.object(QuestionnaireSummaryPDFCreateView, 'get_template_names')
    # @patch('questionnaire.views.get_summary_data')
    # def test_summary_pdf(self, mock_get_summary, mock_template_names):
    #     profile = webdriver.FirefoxProfile()
    #     profile.set_preference('browser.helperApps.neverAsk.openfile',
    #                            'application/pdf')
    #     browser = webdriver.Firefox(
    #         firefox_binary=FirefoxBinary(settings.TESTING_FIREFOX_PATH),
    #         firefox_profile=profile
    #     )
    #     mock_get_summary.return_value = self.data_title_mock
    #     mock_template_names.return_value = 'questionnaire/summary/layout/' \
    #                                        'technologies.html'
    #
    #     response = browser.get(self.url)

    @patch.object(SummaryPDFCreateView, 'get_template_names')
    @patch.object(SummaryPDFCreateView, 'get_summary_data')
    def test_summary_html(self, mock_get_summary, mock_template_names):
        mock_get_summary.return_value = self.data_title_mock
        mock_template_names.return_value = 'summary/layout/technologies.html'

        self.browser.get('{}?as=html'.format(self.url))
        title = self.findBy('class_name', 'tech-output-title')
        self.assertEqual(
            title.text,
            'Success story (Wonderland)'
        )
