# Prevent logging of Elasticsearch queries
import logging
logging.disable(logging.CRITICAL)

from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from unittest.mock import patch

from accounts.client import Typo3Client
from accounts.tests.test_models import create_new_user
from functional_tests.base import FunctionalTest
from sample.tests.test_views import route_home as sample_route_home
from samplemulti.tests.test_views import route_home as samplemulti_route_home
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices


LIST_EMPTY_RESULTS_TEXT = 'No results found.'
TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
class SearchTest(FunctionalTest):

    fixtures = [
        'sample_global_key_values.json', 'sample.json', 'samplemulti.json',
        'sample_questionnaires_search.json']

    def setUp(self):
        super(SearchTest, self).setUp()
        delete_all_indices()
        create_temp_indices(['sample', 'samplemulti'])

    def tearDown(self):
        super(SearchTest, self).tearDown()
        delete_all_indices()

    @patch('questionnaire.views.get_configuration_index_filter')
    def test_search_home(self, mock_get_configuration_index_filter):

        mock_get_configuration_index_filter.return_value = [
            'sample', 'samplemulti']

        # Alice goes to the landing page and sees the search field
        self.browser.get(self.live_server_url + reverse('home'))

        # She enters a search value and submits the search form
        self.findBy('xpath', '//input[@type="search"]').send_keys('key')
        self.apply_filter()

        # She sees that she has been taken to the WOCAT configuration
        # where the search results are listed
        self.assertIn('/wocat/list', self.browser.current_url)
        results = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(results), 3)

        # She sees that this is the same result as when searching in
        # WOCAT (at the top of the page)
        self.findBy('xpath', '//input[@type="search"]').clear()
        self.findBy('xpath', '//input[@type="search"]').send_keys('key')
        self.apply_filter()

        self.assertIn('/wocat/list', self.browser.current_url)
        results = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(results), 3)

    def test_search_sample(self):

        # Alice goes to the home page of the sample configuration and
        # sees the search field at the top of the page.
        self.browser.get(self.live_server_url + reverse(sample_route_home))

        # She enters a search value and submits the search form
        self.findBy('xpath', '//input[@type="search"]').send_keys('key')
        self.set_input_value('search-type', 'sample')
        self.apply_filter()

        # She sees that she has been taken to the SAMPLE configuration
        # where the search results are listed
        self.assertIn('/sample/list', self.browser.current_url)
        results = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(results), 2)

        # Vice versa, the samplemulti configuration only shows results
        # from the samplemulti configuration
        self.browser.get(
            self.live_server_url + reverse(samplemulti_route_home))
        self.findBy('xpath', '//input[@type="search"]').send_keys('key')
        self.set_input_value('search-type', 'samplemulti')
        self.apply_filter()
        results = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(results), 1)


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class SearchTestAdmin(FunctionalTest):

    fixtures = [
        'sample_global_key_values.json', 'sample.json',
        'sample_questionnaires.json']

    def setUp(self):
        super(SearchTestAdmin, self).setUp()
        delete_all_indices()
        user = create_new_user()
        user.is_superuser = True
        user.save()
        self.user = user

    def tearDown(self):
        super(SearchTestAdmin, self).tearDown()
        delete_all_indices()

    def test_search_admin(self, mock_get_user_id):

        # Alice logs in
        self.doLogin(user=self.user)

        # She sees the button to access the search administration in the
        # top navigation bar and clicks it.
        self.clickUserMenu(self.user)
        navbar = self.findBy('class_name', 'top-bar')
        navbar.find_element_by_link_text('Search Index Administration').click()

        # She sees that the active configurations are listed, all of
        # them having no index
        self.findBy(
            'xpath',
            '//tbody/tr[1]/td/span[text()="Sample Core Configuration"]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[1]/td/span/strong[@class="text-warning"]').text,
            'No Index!')
        self.findBy(
            'xpath',
            '//tbody/tr[2]/td/span[text()="Sample Configuration"]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[2]/td/span/strong[@class="text-warning"]').text,
            'No Index!')

        # She creates the index for the sample configuration
        self.findBy('xpath', '//a[contains(@href, "/index/sample/")]').click()

        # She sees the index was created successfully
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[1]/td/span/strong[@class="text-warning"]').text,
            'No Index!')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[2]/td/span/strong[@class="text-warning"]').text,
            '0 / 2')

        # She updates the newly created index
        self.findBy('xpath', '//a[contains(@href, "/update/sample/")]').click()

        # She sees that the index was updated successfully
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[1]/td/span/strong[@class="text-warning"]').text,
            'No Index!')
        self.findByNot(
            'xpath', '//tbody/tr[2]/td/span/strong[@class="text-warning"]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[2]/td/span/strong[@class="text-ok"]').text,
            '2 / 2')

        # She decides to delete all indices
        self.findBy('xpath', '//a[@href="/en/search/delete/"]').click()

        # She sees that all indices were deleted
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy(
            'xpath',
            '//tbody/tr[1]/td/span[text()="Sample Core Configuration"]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[1]/td/span/strong[@class="text-warning"]').text,
            'No Index!')
        self.findBy(
            'xpath',
            '//tbody/tr[2]/td/span[text()="Sample Configuration"]')
        self.assertEqual(
            self.findBy(
                'xpath',
                '//tbody/tr[2]/td/span/strong[@class="text-warning"]').text,
            'No Index!')
