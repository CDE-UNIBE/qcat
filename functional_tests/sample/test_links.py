from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from unittest.mock import patch

from accounts.client import Typo3Client
from accounts.models import User
from functional_tests.base import FunctionalTest
from sample.tests.test_views import route_questionnaire_list, \
    route_questionnaire_new
from samplemulti.tests.test_views import route_questionnaire_new as \
    route_questionnaire_new_samplemulti, route_questionnaire_list as \
    route_questionnaire_list_samplemulti
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices

TEST_INDEX_PREFIX = 'qcat_test_prefix_'


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class LinkTests(FunctionalTest):

    fixtures = [
        'groups_permissions.json', 'global_key_values.json', 'sample.json',
        'samplemulti', 'sample_samplemulti_questionnaires.json']

    """
    1
        configurations: sample
        code: sample_1
        key_1 (en): This is the first key
        links: 3

    2
        configurations: sample
        code: sample_2
        key_1 (en): Foo
        links: -

    3
        configurations: samplemulti
        code: samplemulti_1
        key_1 (en): This is key 1a
        links: 1

    4
        configurations: samplemulti
        code: samplemulti_2
        key_1 (en): This is key 1b
        links: -
    """

    def setUp(self):
        super(LinkTests, self).setUp()
        delete_all_indices()
        create_temp_indices(['sample', 'samplemulti'])

    def tearDown(self):
        super(LinkTests, self).tearDown()
        delete_all_indices()

    def test_show_only_one_linked_version(self, mock_get_user_id):

        # Alice logs in
        user = User.objects.get(pk=101)
        self.doLogin(user=user)

        # She goes to the SAMPLE questionnaire and sees the link
        self.open_questionnaire_details('sample', identifier='sample_1')
        self.findBy(
            'xpath', '//a[contains(text(), "This is key 1a")]').click()

        # She goes to the MULTISAMPLE questionnaire and sees the link
        section_xpath = '//section[@id="mcat_1"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            sample_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-sample")]//a['
                         'contains(text(), "This is the first key.")]'.format(
                    xpath))
            self.assertEqual(len(sample_links), 1)
            self.findByNot('xpath', '{}//article[contains(@class, "is-sample")]//'
                                 'span[contains(@class, "tech-status")]'.format(
                xpath))

        # She edits the MULTISAMPLE questionnaire and sees only one
        # version is linked (still the same)
        self.review_action('edit')
        self.findBy(
            'xpath',
            '//a[contains(text(), "Edit this section")][1]').click()
        self.findBy('name', 'mqg_01-0-original_mkey_01').send_keys(
            ' (changed)')

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that only one questionnaire is linked
        self.toggle_all_sections()
        section_xpath = '//section[@id="mcat_1"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            sample_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-sample")]//a['
                         'contains(text(), "This is the first key.")]'.format(
                    xpath))
            self.assertEqual(len(sample_links), 1)
            self.findByNot('xpath',
                           '{}//article[contains(@class, "is-sample")]//'
                           'span[contains(@class, "tech-status")]'.format(
                               xpath))

        # She goes to the SAMPLE questionnaire and sees only one version
        # is linked (the pending one)
        self.wait_for('xpath', '//a[contains(text(), "This is the first key.")]')
        self.findBy(
            'xpath', '//a[contains(text(), "This is the first key.")]').click()

        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "This is key 1a (changed)")]'.format(
                    xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findBy(
                'xpath',
                '{}//article[contains(@class, "is-samplemulti")]//span['
                'contains(@class, "tech-status") and contains('
                '@class, "is-draft")]'.format(xpath))

        url = self.browser.current_url

        # She logs out and sees only one questionnaire is linked (the
        # active one)
        self.doLogout()
        self.browser.get(url)

        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "This is key 1a")]'.format(
                    xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findByNot(
                'xpath',
                '{}//article[contains(@class, "is-samplemulti")]//span['
                'contains(@class, "tech-status")]'.format(xpath))

        # She logs in as a different user and sees only one version is
        # linked (the active one)
        user = User.objects.get(pk=102)
        self.doLogin(user=user)
        self.browser.get(url)
        self.toggle_all_sections()
        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "This is key 1a")]'.format(
                    xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findByNot(
                'xpath',
                '{}//article[contains(@class, "is-samplemulti")]//span['
                'contains(@class, "tech-status")]'.format(xpath))

    def test_add_only_one_side_of_link_to_es_when_publishing(
            self, mock_get_user_id):

        # Alice logs in
        user_alice = User.objects.get(pk=101)
        user_alice.groups = [Group.objects.get(pk=3), Group.objects.get(pk=4)]
        self.doLogin(user=user_alice)

        # She goes to the list page
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list))

        # She sees two entries
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)

        # She goes to the SAMPLEMULTI list view and sees 2 entries
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list_samplemulti))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)

        # She enters a new SAMPLE questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        self.click_edit_section('cat_1')
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Foo')
        self.submit_form_step()

        sample_url = self.browser.current_url

        # She also enters a new SAMPLEMULTI questionnaire which links to the
        # newly created SAMPLE questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_samplemulti))
        self.click_edit_section('mcat_1')
        self.findBy('name', 'mqg_01-0-original_mkey_01').send_keys('Bar')
        self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]'
                     '[1]').send_keys('Foo')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Foo"'
            ']').click()
        self.submit_form_step()

        samplemulti_url = self.browser.current_url

        # She goes to the list view and sees there are still only 2 entries
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)

        # She goes to the list view of SAMPLEMULTI and sees there are still
        # only 2 entries
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list_samplemulti))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)

        # She goes back to the SAMPLEMULTI questionnaire and publishes it
        self.browser.get(samplemulti_url)
        self.review_action('submit')
        self.review_action('review')
        self.review_action('publish')

        # She goes to the list view and sees there are still 2 entries (as the
        # SAMPLEMULTI questionnaires are not visible from SAMPLE)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 2)

        # She goes to the SAMPLEMULTI list view and sees there are now 3 entries
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list_samplemulti))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 3)

        # The first of the list is the newly created one, it does not have a
        # link attached (as the other side of the link is still "draft")
        self.findByNot(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//ul['
                     'contains(@class, "tech-attached")]/li/a')

        # She goes to the SAMPLE questionnaire and publishes it
        self.browser.get(sample_url)
        self.wait_for('xpath', '//a[@data-reveal-id="confirm-submit"]')
        self.review_action('submit')
        self.review_action('review')
        self.review_action('publish')

        # She goes to the SAMPLE list view and sees there are now 3 entries
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 3)

        # The first of the list is the newly created one and it does have a link
        # attached
        link_count = self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//ul['
                     'contains(@class, "tech-attached")]/li/a')
        self.assertEqual(link_count.text, '')

        # She goes to the SAMPLEMULTI list view and sees there are 3 entries
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_list_samplemulti))
        list_entries = self.findManyBy(
            'xpath', '//article[contains(@class, "tech-item")]')
        self.assertEqual(len(list_entries), 3)

        # The first of the list is the newly created one and it does now have a
        # link attached
        link_count = self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]//ul['
                     'contains(@class, "tech-attached")]/li/a')
        self.assertEqual(link_count.text, '')

    def test_do_not_add_duplicate_links_when_editing(self, mock_get_user_id):
        # Alice logs in
        user_alice = User.objects.get(pk=101)
        user_alice.groups = [Group.objects.get(pk=3), Group.objects.get(pk=4)]
        self.doLogin(user=user_alice)

        # She enters a new SAMPLE questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new))
        self.click_edit_section('cat_1')
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('Sample Q1')
        self.submit_form_step()

        sample_url = self.browser.current_url

        # She also enters a new SAMPLEMULTI questionnaire which links to the
        # newly created SAMPLE questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_new_samplemulti))
        self.click_edit_section('mcat_1')
        self.findBy('name', 'mqg_01-0-original_mkey_01').send_keys(
            'Samplemulti Q1')
        self.findBy(
            'xpath', '//input[contains(@class, "link-search-field")]'
                     '[1]').send_keys('Sample Q1')
        self.wait_for('xpath', '//li[@class="ui-menu-item"]')
        self.findBy(
            'xpath',
            '//li[@class="ui-menu-item"]//strong[text()="Sample Q1"'
            ']').click()
        self.submit_form_step()

        samplemulti_url = self.browser.current_url

        # She sees the added link in 2 places, but each time only once!
        section_xpath = '//section[@id="mcat_1"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            sample_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-sample")]//a['
                         'contains(text(), "Sample Q1")]'.format(xpath))
            self.assertEqual(len(sample_links), 1)
            self.findBy('xpath', '{}//article[contains(@class, "is-sample")]//'
                                 'span[contains(@class, "tech-status") and '
                                 'contains(@class, "is-draft")]'.format(xpath))

        # She goes to the Sample Questionnaire. Again, she sees the link in 2
        # places, but each time only once!
        self.browser.get(sample_url)
        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "Samplemulti Q1")]'.format(xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//span['
                         'contains(@class, "tech-status") and contains('
                         '@class, "is-draft")]'.format(xpath))

        # She submits the Sample Questionnaire
        self.review_action('submit')

        # She edits the Questionnaire (only opens the section with the link and
        # closes it again)
        self.findBy('xpath', '//a[text()="Edit" and @type="submit"]').click()
        self.click_edit_section('cat_1')
        self.submit_form_step()

        # She sees that there is still only one link visible
        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "Samplemulti Q1")]'.format(xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findBy(
                'xpath',
                '{}//article[contains(@class, "is-samplemulti")]//span['
                'contains(@class, "tech-status") and contains('
                '@class, "is-draft")]'.format(xpath))

        # She goes to the Samplmulti Questionnaire and sees the link (only once)
        self.browser.get(samplemulti_url)
        section_xpath = '//section[@id="mcat_1"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            sample_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-sample")]//a['
                         'contains(text(), "Sample Q1")]'.format(xpath))
            self.assertEqual(len(sample_links), 1)
            self.findBy('xpath', '{}//article[contains(@class, "is-sample")]//'
                                 'span[contains(@class, "tech-status") and '
                                 'contains(@class, "is-submitted")]'.format(
                xpath))

        # She submits the Samplemulti Questionnaire
        self.review_action('submit')

        # She edits the Questionnaire (only opens the section with the link and
        # closes it again)
        self.findBy('xpath', '//a[text()="Edit" and @type="submit"]').click()
        self.click_edit_section('mcat_1')
        self.submit_form_step()

        self.browser.get(samplemulti_url)
        section_xpath = '//section[@id="mcat_1"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            sample_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-sample")]//a['
                         'contains(text(), "Sample Q1")]'.format(xpath))
            self.assertEqual(len(sample_links), 1)
            self.findBy('xpath', '{}//article[contains(@class, "is-sample")]//'
                                 'span[contains(@class, "tech-status") and '
                                 'contains(@class, "is-submitted")]'.format(
                xpath))

        # From Sample Questionnaire, still only one version is linked
        self.browser.get(sample_url)
        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "Samplemulti Q1")]'.format(xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findBy(
                'xpath',
                '{}//article[contains(@class, "is-samplemulti")]//span['
                'contains(@class, "tech-status") and contains('
                '@class, "is-submitted")]'.format(xpath))

        # She publishes the Sample Questionnaire and still, only one link
        self.review_action('review')
        self.review_action('publish')
        section_xpath = '//section[@id="cat_5"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            samplemulti_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-samplemulti")]//'
                         'a[contains(text(), "Samplemulti Q1")]'.format(xpath))
            self.assertEqual(len(samplemulti_links), 1)
            self.findBy(
                'xpath',
                '{}//article[contains(@class, "is-samplemulti")]//span['
                'contains(@class, "tech-status") and contains('
                '@class, "is-submitted")]'.format(xpath))

        # From Samplemulti Questionnaire, still only one version is linked
        self.browser.get(samplemulti_url)
        section_xpath = '//section[@id="mcat_1"]'
        link_xpath = '//section[@id="links"]'
        for xpath in [section_xpath, link_xpath]:
            sample_links = self.findManyBy(
                'xpath', '{}//article[contains(@class, "is-sample")]//a['
                         'contains(text(), "Sample Q1")]'.format(xpath))
            self.assertEqual(len(sample_links), 1)
            self.findByNot('xpath', '{}//article[contains(@class, "is-sample")]//'
                                 'span[contains(@class, "tech-status")]'.format(
                xpath))
