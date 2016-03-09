from unittest.mock import patch, MagicMock, PropertyMock

from requests.exceptions import BaseHTTPError

from qcat.tests import TestCase
from .test_models import create_new_user
from ..client import typo3_client, Typo3Client


class TestClient(TestCase):
    def setUp(self):
        self.user = create_new_user()

    def api_login_response(self, status_code, login_status='foo'):
        api_response = MagicMock()
        api_response.configure_mock(status_code=status_code)
        api_response.json = lambda: {'status': login_status}
        return api_response

    @patch('requests.post')
    def test_api_login_status_code(self, mock_post):
        mock_post.return_value = self.api_login_response(404)
        login = typo3_client.api_login()
        self.assertIsNone(login)

    @patch('requests.post')
    def test_api_login_status_invalid(self, mock_post):
        mock_post.return_value = self.api_login_response(200)
        login = typo3_client.api_login()
        self.assertIsNone(login)

    @patch('requests.post')
    def test_api_login_status_valid(self, mock_post):
        mock_post.return_value = self.api_login_response(200, 'logged-in')
        login = typo3_client.api_login()
        self.assertIsNotNone(login)

    @patch.object(Typo3Client, 'get_user_information')
    def test_get_and_update_django_user(self, mock_user_information):
        user_mock = dict(
            last_name='last_test',
            first_name='first_test',
            username=self.user.email,
            usergroup=[],
        )
        with patch.object(Typo3Client, 'get_user_information') as user_info:
            user_info.return_value = user_mock
            user = typo3_client.get_and_update_django_user(self.user.id, 'foo')
            self.assertEqual(user.lastname, 'last_test')
            self.assertEqual(user.firstname, 'first_test')
            self.assertEqual(user.email, self.user.email)
            self.assertEqual(user, self.user)

    def test_get_logout_url(self):
        url = typo3_client.get_logout_url('foo')
        self.assertTrue(url.endswith('foo'))

    @patch('requests.post')
    @patch('accounts.client.typo3_client.api_login')
    def test_get_user_id_no_login(self, mock_request_post, mock_api_login):
        mock_request_post.return_value = None
        self.assertIsNone(typo3_client.get_user_id('foo'))

    @patch('accounts.client.typo3_client.api_login')
    def test_get_user_id_invalid_response(self, mock_api_login):
        mock_api_login.return_value = None
        self.assertIsNone(typo3_client.get_user_id('foo'))

    @patch('requests.post')
    def test_get_user_id_valid_response(self, mock_request_post):
        with patch.object(Typo3Client, 'api_login') as api_login:
            api_login.return_value = MagicMock()
            request_post = MagicMock()
            request_post.status_code = 200
            request_post.ok = PropertyMock(return_value=True)
            request_post.json = lambda: dict(
                success=True, login=True, userid=123
            )
            mock_request_post.return_value = request_post
            self.assertEqual(typo3_client.get_user_id('foo'), 123)

    @patch('requests.post')
    def test_get_user_info(self, mock_request_post):
        with patch.object(Typo3Client, 'api_login') as api_login:
            api_login.return_value = MagicMock()
            request_post = MagicMock()
            request_post.status_code = 200
            request_post.ok = PropertyMock(return_value=True)
            request_post.json = lambda: dict(success=True)
            mock_request_post.return_value = request_post
            self.assertIsInstance(
                typo3_client.get_user_information('123'), dict
            )

    @patch('requests.post')
    def test_remote_login_404(self, mock_request_post):
        mock_request_post.side_effect = BaseHTTPError(MagicMock(status=404))
        self.assertIsNone(typo3_client.remote_login('foo', 'bar'))

    @patch('requests.post')
    def test_search_users(self, mock_request_post):
        with patch.object(Typo3Client, 'api_login') as api_login:
            api_login.return_value = MagicMock()
            request_post = MagicMock()
            request_post.status_code = 200
            request_post.ok = PropertyMock(return_value=True)
            request_post.json = lambda: dict(success=True)
            mock_request_post.return_value = request_post
            self.assertIsInstance(
                typo3_client.search_users('foo'), dict
            )

    def test_update_user(self):
        # This is tested within test_models.
        pass
