from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from functional_tests.base import FunctionalTest

from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices
from wocat.tests.test_views import route_questionnaire_list as route_wocat_list


TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@override_settings(
    ES_INDEX_PREFIX=TEST_INDEX_PREFIX,
    LANGUAGES=(('en', 'English'), ('es', 'Spanish'), ('fr', 'French')))
class ListTest(FunctionalTest):

    fixtures = [
        'global_key_values.json', 'wocat.json', 'technologies.json',
        'unccd.json', 'technologies_questionnaires.json',
        'unccd_questionnaires.json']

    def setUp(self):
        super(ListTest, self).setUp()
        delete_all_indices()
        create_temp_indices(['technologies', 'approaches', 'wocat', 'unccd',
                             'cca', 'watershed'])

    def tearDown(self):
        super(ListTest, self).tearDown()
        delete_all_indices()

    def test_list_is_available(self):

        # She goes to the WOCAT list and sees that both Technologies and
        # UNCCD practices are listed, each with details.
        self.browser.get(self.live_server_url + reverse(route_wocat_list))

        results = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(results), 4)

        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//a['
            'contains(text(), "UNCCD practice 2")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//p['
            'contains(text(), "This is the description of the second UNCCD '
            'practice.")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//a['
            'contains(text(), "WOCAT Tech 2 en español")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//p['
            'contains(text(), "Descripción 2 en español")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[3]//a['
            'contains(text(), "UNCCD practice 1")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[3]//p['
            'contains(text(), "This is the description of the first UNCCD '
            'practice.")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[4]//a['
            'contains(text(), "WOCAT Technology 1")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[4]//p['
            'contains(text(), "This is the definition of the first WOCAT '
            'Technology.")]')

        # Alice applies the type filter and sees that only technologies are
        # listed
        self.findBy('id', 'search-type-display').click()
        self.findBy('xpath', '//li/a[@data-type="technologies"]').click()
        self.apply_filter()

        results = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(results), 2)

        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//a['
            'contains(text(), "WOCAT Tech 2 en español")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//p['
            'contains(text(), "Descripción 2 en español")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//a['
            'contains(text(), "WOCAT Technology 1")]')
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[2]//p['
            'contains(text(), "This is the definition of the first WOCAT '
            'Technology.")]')

    def test_filter(self):

        # Alice goes to the list view and filters by technologies.
        self.browser.get(self.live_server_url + reverse(route_wocat_list))
        self.findBy('id', 'search-type-display').click()

        self.wait_for('xpath', '//li/a[@data-type="technologies"]')
        self.findBy('xpath', '//li/a[@data-type="technologies"]').click()
        self.apply_filter()

        # She also filters by country
        self.findBy('xpath', '//div[contains(@class,'
                             ' "chosen-container")]').click()

        self.findBy(
            'xpath', '//ul[@class="chosen-results"]/li[contains(text(), '
                     '"Switzerland")]').click()
        self.apply_filter()

        # She sees that she has been redirected to the list view and the filter
        # is set, only 1 entry is visible
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 1)

        # The filter was added to the list of active filters
        active_filter_panel = self.findBy(
            'xpath', '//div[@id="active-filters"]/div')
        self.assertTrue(active_filter_panel.is_displayed())
        active_filters = self.findManyBy(
            'xpath', '//div[@id="active-filters"]//li')
        self.assertEqual(len(active_filters), 1)
        filter_1 = self.findBy('xpath', '//div[@id="active-filters"]//li[1]')
        self.assertEqual(filter_1.text, 'Country: Switzerland')
