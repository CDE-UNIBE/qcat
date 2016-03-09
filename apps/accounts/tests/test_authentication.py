from django.contrib.auth import get_user_model
from unittest.mock import patch
from qcat.tests import TestCase
from ..authentication import WocatAuthenticationBackend
from ..client import typo3_client, Typo3Client

User = get_user_model()


def get_mock_validate_session_values():
    """
    Returns mock values that correspond to the actual validate_session
    function in accounts.authentication.
    """
    return 1


def get_mock_user_information_values():
    """
    Returns mock values that correspond to the actual
    get_user_information function in accounts.authentication.
    """
    return {
        'uid': 1,
        'username': 'foo@bar.com',
        'first_name': 'Foo',
        'last_name': 'Bar',
    }


class AuthenticateTest(TestCase):

    def setUp(self):
        self.backend = WocatAuthenticationBackend()
        user, created = User.objects.get_or_create(
            id=1, email='foo@bar.com',
            defaults={'lastname': 'Foo', 'firstname': 'Bar'}
        )
        self.user = user

    @patch.object(Typo3Client, 'get_user_information')
    def test_creates_new_user_if_necessary(self, mock_get_user_information):
        mock_get_user_information.return_value = \
            get_mock_user_information_values()
        user = typo3_client.get_and_update_django_user(1, 1)
        self.assertEqual(1, user.id)


class ValidateSessionTest(TestCase):

    @patch('accounts.client.typo3_client.get_user_id')
    def test_returns_None_if_api_login_is_not_valid(self, mock_api_login):
        mock_api_login.return_value = None
        user_id = typo3_client.get_user_id('foo')
        self.assertIsNone(user_id)


@patch('accounts.client.typo3_client.api_login')
class GetUserInformationTest(TestCase):

    def test_returns_None_if_api_login_is_not_valid(self, mock_api_login):
        mock_api_login.return_value = None
        user_info = typo3_client.get_user_information(1)
        self.assertIsNone(user_info)


class SearchUsersTest(TestCase):

    @patch.object(Typo3Client, 'api_login')
    def test_returns_empty_dict_if_api_login_is_not_valid(
            self, mock_api_login):
        mock_api_login.return_value = None
        search_results = typo3_client.search_users(name='foo')
        self.assertEqual(search_results, {})
