from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from unittest.mock import patch

from accounts.client import Typo3Client
from accounts.models import User
from functional_tests.base import FunctionalTest
from sample.tests.test_views import (
    # get_position_of_category,
    # route_home,
    route_questionnaire_details,
    # route_questionnaire_list,
    # route_questionnaire_new,
)
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices

from nose.plugins.attrib import attr  # noqa
# @attr('foo')

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
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy(
            'xpath', '//a[contains(text(), "This is key 1a")]').click()

        # She goes to the MULTISAMPLE questionnaire and sees the link
        links = self.findManyBy(
            'xpath', '//a[contains(text(), "This is the first key.")]')
        self.assertEqual(len(links), 1)

        # She edits the MULTISAMPLE questionnaire and sees only one
        # version is linked (still the same)
        self.findBy('xpath', '//a[contains(text(), "Edit")]').click()
        self.findBy(
            'xpath',
            '//a[contains(text(), "Edit this section")][1]').click()
        self.findBy('name', 'mqg_01-0-original_mkey_01').send_keys(
            ' (changed)')

        # She submits the step
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She submits the questionnaire
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')

        # She sees that only one questionnaire is linked
        links = self.findManyBy(
            'xpath', '//a[contains(text(), "This is the first key.")]')
        self.assertEqual(len(links), 1)

        # She goes to the SAMPLE questionnaire and sees only one version
        # is linked (the pending one)
        self.findBy(
            'xpath', '//a[contains(text(), "This is the first key.")]').click()

        links = self.findManyBy(
            'xpath', '//a[contains(text(), "This is key 1a")]')
        self.assertEqual(len(links), 1)
        self.findBy(
            'xpath', '//a[contains(text(), "This is key 1a (changed)")]')

        url = self.browser.current_url

        # She logs out and sees only one questionnaire is linked (the
        # active one)
        self.doLogout()
        self.browser.get(url)
        links = self.findManyBy(
            'xpath', '//a[contains(text(), "This is key 1a")]')
        self.assertEqual(len(links), 1)
        self.findByNot(
            'xpath', '//a[contains(text(), "This is key 1a (changed)")]')

        # She logs in as a different user and sees only one version is
        # linked (the active one)
        user = User.objects.get(pk=102)
        self.doLogin(user=user)
        self.browser.get(url)
        links = self.findManyBy(
            'xpath', '//a[contains(text(), "This is key 1a")]')
        self.assertEqual(len(links), 1)
        self.findByNot(
            'xpath', '//a[contains(text(), "This is key 1a (changed)")]')
