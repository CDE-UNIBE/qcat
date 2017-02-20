from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from unittest.mock import patch

from django.test.utils import override_settings

from accounts.client import Typo3Client
from accounts.models import User
from accounts.tests.test_models import create_new_user
from accounts.tests.test_views import accounts_route_user, \
    accounts_route_questionnaires
from functional_tests.base import FunctionalTest
from search.index import delete_all_indices
from search.tests.test_index import create_temp_indices
from unccd.tests.test_views import route_home
from sample.tests.test_views import route_questionnaire_details, \
    route_questionnaire_list

TEST_INDEX_PREFIX = 'qcat_test_prefix_'


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


@override_settings(ES_INDEX_PREFIX=TEST_INDEX_PREFIX)
@patch.object(Typo3Client, 'get_user_id')
class FlaggingTest(FunctionalTest):

    fixtures = ['groups_permissions', 'global_key_values', 'flags', 'sample',
                'unccd', 'sample_questionnaires_5']

    def setUp(self):
        super(FlaggingTest, self).setUp()
        delete_all_indices()
        create_temp_indices(['sample', 'unccd'])

    def tearDown(self):
        super(FlaggingTest, self).tearDown()
        delete_all_indices()

    def test_unccd_focal_point(self, mock_get_user_id):

        unccd_user = create_new_user()
        unccd_user.update(usergroups=[{
            'name': 'UNCCD Focal Point',
            'unccd_country': 'CHE',
        }])

        # Alice logs in
        self.doLogin(user=unccd_user)

        # She goes to her user profile and sees that she is identified as UNCCD
        # focal point for her country.
        self.browser.get(self.live_server_url + reverse(
            accounts_route_user, kwargs={'pk': unccd_user.id}))

        self.findBy('xpath', '//*[contains(text(), "UNCCD focal point")]')
        self.findBy('xpath', '//a[contains(text(), "Switzerland")]')

    def test_unccd_flag_elasticsearch(self, mock_get_user_id):
        unccd_user = create_new_user(id=1, email='a@b.com')
        unccd_user.update(usergroups=[{
            'name': 'UNCCD Focal Point',
            'unccd_country': 'CHE',
        }])
        user_publisher = create_new_user(id=2, email='c@d.com')
        user_publisher.groups = [
            Group.objects.get(pk=3), Group.objects.get(pk=4)]
        user_publisher.save()

        # Alice logs in as UNCCD focal point
        self.doLogin(user=unccd_user)

        # She flags a questionnaire
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.review_action('flag-unccd')
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # A publisher publishes it
        self.doLogin(user=user_publisher)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findBy(
            'xpath', '//a[contains(@href, "sample/edit/")]')
        self.review_action('publish')
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # He sees the questionnaire is in the list, with the flag visible
        self.browser.get(
            self.live_server_url + reverse(route_questionnaire_list))
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]'
                     '//span[contains(@class, "is-unccd_bp")]')

        # He goes to the page where he sees the questionnaires of user UNCCD
        # and sees the flag there as well.
        # self.browser.get(self.live_server_url + reverse(
        #     accounts_route_questionnaires, kwargs={'user_id': unccd_user.id}))
        # self.findBy(
        #     'xpath', '(//article[contains(@class, "tech-item")])[1]'
        #              '//span[contains(@class, "is-unccd_bp")]')

        # UNCCD user logs in and goes to the page where he sees his own
        # questionnaires (this one queries the database) and sees the
        # questionnaire with the flag there as well.
        self.doLogin(user=unccd_user)
        self.browser.get(self.live_server_url + reverse(
            accounts_route_questionnaires))
        self.findBy(
            'xpath', '(//article[contains(@class, "tech-item")])[1]'
                     '//span[contains(@class, "is-unccd_bp")]')

    def test_unccd_flag(self, mock_get_user_id):

        unccd_user = create_new_user(id=1, email='a@b.com')
        unccd_user.update(usergroups=[{
            'name': 'UNCCD Focal Point',
            'unccd_country': 'CHE',
        }])
        user_editor = User.objects.get(pk=101)
        user_publisher = create_new_user(id=2, email='c@d.com')
        user_publisher.groups = [
            Group.objects.get(pk=3), Group.objects.get(pk=4)]
        user_publisher.save()

        # Alice logs in
        self.doLogin(user=unccd_user)

        # She goes to a public Questionnaire which is NOT in her country where
        # she does NOT see a possibility to flag the questionnaire as UNCCD best
        # practice.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_3'}))
        self.findByNot('xpath', '//input[@name="flag-unccd"]')

        # She goes to a public Questionnaire which is in her country and now she
        # sees a possibility to flag it.
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))

        # She flags the questionnaire
        self.review_action('flag-unccd')

        # She sees the new UNCCD flag
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # She sees the status flag
        self.findBy('xpath', '//span[contains(@class, "is-reviewed")]')

        # She sees a notice that the new version is now reviewed and it is
        # waiting to be published
        self.findBy('xpath', '//div[contains(@class, "review-panel")]')
        self.findByNot('xpath', '//input[@name="publish"]')

        # An editor logs in and sees the flag. He cannot edit the questionnaire.
        self.doLogin(user=user_editor)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findByNot(
            'xpath', '//a[contains(@href, "sample/edit/")]')

        # A publisher publishes the Questionnaire
        self.doLogin(user=user_publisher)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findBy(
            'xpath', '//a[contains(@href, "sample/edit/")]')
        self.review_action('publish')

        # It is public and flagged
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findByNot('xpath', '//span[contains(@class, "is-reviewed")]')

        # The UNCCD user logs in and does not see the option to flag the
        # questionnaire again
        self.doLogin(user=unccd_user)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findByNot('xpath', '//input[@name="flag-unccd"]')

        # However, he sees the option to unflag the Questionnaire
        self.review_action('unflag-unccd', exists_only=True)

        # An editor makes an edit on the Questionnaire
        self.doLogin(user=user_editor)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.review_action('edit')
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # He changes some values
        self.findBy(
            'xpath', '(//a[contains(text(), "Edit this section")])[2]').click()
        self.findBy('name', 'qg_1-0-original_key_1').clear()
        self.findBy('name', 'qg_1-0-original_key_1').send_keys('asdf')

        # She saves the step which creates a new version
        self.findBy('id', 'button-submit').click()
        self.findBy('xpath', '//div[contains(@class, "success")]')
        self.findBy('xpath', '//span[contains(@class, "is-draft")]')

        # She sees that the new version also has the UNCCD flag
        self.findBy('xpath', '//p[text()="asdf"]')
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # He submits the Questionnaire
        self.review_action('submit')
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findBy('xpath', '//span[contains(@class, "is-submitted")]')

        # The UNCCD user logs in and still sees the public version
        self.doLogin(user=unccd_user)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findByNot('xpath', '//span[contains(@class, "is-draft")]')

        # He cannot unflag the Questionnaire as it has a version in the review
        # cycle.
        self.review_action('unflag-unccd', expected_msg_class='error')

        # The UNCCD flag is still there
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # A publisher publishes the Questionnaire
        self.doLogin(user=user_publisher)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findBy(
            'xpath', '//a[contains(@href, "sample/edit/")]')
        self.review_action('review')
        self.review_action('publish')

        # UNCCD user comes along again and tries to unflag the questionnaire
        # again. This time, it works and the flag is removed.
        self.doLogin(user=unccd_user)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.review_action('unflag-unccd')

        # As the user is not linked to the questionnaire anymore, he does not
        # see the reviewed version (no privileges). Instead, he sees the public
        # version
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findByNot('xpath', '//span[contains(@class, "is-reviewed")]')

        # Although he sees the button to (again) unflag the questionnaire,
        # nothing happens if he clicks it
        self.review_action('unflag-unccd', expected_msg_class='error')
        self.findBy('xpath', '//span[contains(@class, "is-unccd_bp")]')

        # The publisher publishes the Questionnaire and now the flag is gone.
        self.doLogin(user=user_publisher)
        self.browser.get(self.live_server_url + reverse(
            route_questionnaire_details, kwargs={'identifier': 'sample_1'}))
        self.findByNot('xpath', '//span[contains(@class, "is-unccd_bp")]')
        self.findBy(
            'xpath', '//a[contains(@href, "sample/edit/")]')
        self.review_action('publish')
        self.findByNot('xpath', '//span[contains(@class, "is-unccd_bp")]')
