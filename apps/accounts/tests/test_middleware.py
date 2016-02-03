from unittest.mock import patch, MagicMock

from django.conf import settings

from qcat.tests import TestCase
from .test_models import create_new_user
from ..middleware import WocatAuthenticationMiddleware


class TestWocatAuthenticationMiddleware(TestCase):
    """
    Test the core functionality of the custom middleware.
    """
    def setUp(self):
        self.user = create_new_user()

    def test_logout_invalid_session_id(self):
        request = MagicMock()
        request.user.is_authenticated = MagicMock(return_value=True)
        with patch('accounts.client.typo3_client.get_user_id') as get_user_id:
            get_user_id.return_value = None
            WocatAuthenticationMiddleware().process_request(request)
            self.assertFalse(request.user.is_authenticated())

    # def test_login_valid_session_id(self):
    #     """This works when running account.tests.test_middleware only."""
    #     request = MagicMock()
    #     request.user.is_authenticated = MagicMock(return_value=False)
    #     request.COOKIES = {settings.AUTH_COOKIE_NAME: 'foo'}
    #     with patch('accounts.client.typo3_client.get_user_id') as get_user_id:
    #         get_user_id.return_value = self.user.id
    #         with patch(
    #             'accounts.client.typo3_client.get_and_update_django_user'
    #         ) as get_and_update_django_user:
    #             get_and_update_django_user.return_value = self.user
    #             WocatAuthenticationMiddleware().process_request(request)
    #             self.assertEqual(request.user, self.user)

    def test_expired_cookie(self):
        request = MagicMock()
        request.user.is_authenticated = MagicMock(return_value=True)
        request.COOKIES = {settings.AUTH_COOKIE_NAME: 'foo'}
        with patch('accounts.client.typo3_client.get_user_id') as get_user_id:
            get_user_id.return_value = None
            WocatAuthenticationMiddleware().process_request(request)
            self.assertFalse(request.user.is_authenticated())

    # def test_force_login(self):
    #     """
    #     This sometimes fails, as patching get_user_id doesnt always work.
    #     """
    #     request = MagicMock()
    #     request.user.is_authenticated = MagicMock(return_value=True)
    #     request.COOKIES = {
    #         settings.AUTH_COOKIE_NAME: 'foo',
    #         settings.ACCOUNTS_ENFORCE_LOGIN_NAME: True
    #     }
    #     with patch('accounts.client.typo3_client.get_user_id') as get_user_id:
    #         get_user_id.return_value = True
    #         instance = WocatAuthenticationMiddleware()
    #         instance.process_request(request)
    #         self.assertTrue(instance.refresh_login_timeout)
