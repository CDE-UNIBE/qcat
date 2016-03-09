from datetime import timedelta
from django.conf import settings
from django.contrib.auth import logout, login
from django.utils import dateparse
from django.utils.timezone import now, utc

from qcat.context_managers import ignored
from .client import typo3_client


class WocatAuthenticationMiddleware(object):
    """
    Middleware checking the (remote) authentication for each request.
    """

    def __init__(self):
        self.delete_auth_cookie = False
        self.refresh_login_timeout = False

    def process_request(self, request):
        """
        Handle the login requirements for the users. Users can login on
        wocat.net - if so, we must login the users with the cookie set on
        wocat.net.

        Re-authentication of the cookie is forced every n seconds (see conf).

        Args:
            request: A http request
        """
        session_id = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        login_timeout = request.get_signed_cookie(
            key=settings.ACCOUNTS_ENFORCE_LOGIN_COOKIE_NAME,
            salt=settings.ACCOUNTS_ENFORCE_LOGIN_SALT,
            default=None
        )
        force_login = request.session.get(settings.ACCOUNTS_ENFORCE_LOGIN_NAME)

        # For authenticated users, check validity of session_id. If not, log the
        # user out.
        if request.user.is_authenticated():
            if not session_id:
                self.logout(request)
            if force_login or self.login_timeout_expired(login_timeout):
                if typo3_client.get_user_id(session_id):
                    # Login still OK - refresh the cookie.
                    self.refresh_login_timeout = True
                else:
                    self.logout(request)

        # If the user isn't authenticated, but a valid session_id exists, log
        # the user in.
        elif session_id:
            user_id = typo3_client.get_user_id(session_id)
            if not user_id:
                # Delete auth cookie for invalid users.
                self.delete_auth_cookie = True
            else:
                user = typo3_client.get_and_update_django_user(
                    user_id, session_id
                )

                if user_id and user:
                    user.backend = 'accounts.authentication.' \
                                   'WocatAuthenticationBackend'
                    login(request, user)
                    self.refresh_login_timeout = True

        if force_login:
            with ignored(KeyError):
                del request.session[settings.ACCOUNTS_ENFORCE_LOGIN_NAME]

    def login_timeout_expired(self, login_timeout=None):
        """
        Check if login must be refreshed; this interval can be set in the
        accounts settings.

        Returns: boolean

        Args:
            login_timeout: datetime

        """
        if not login_timeout:
            return False
        expiry = dateparse.parse_datetime(login_timeout).replace(tzinfo=utc) + \
            timedelta(seconds=settings.ACCOUNTS_ENFORCE_LOGIN_TIMEOUT)
        return True if now() > expiry else False

    def logout(self, request):
        """

        Args:
            request: A http request

        Returns:

        """
        # There is an invalid session ID, mark it for removal.
        logout(request)
        self.delete_auth_cookie = True

    def process_response(self, request, response):
        """
        Function being called for each response. Used to delete a
        cookie.

        Args:
            response:
            request:
        """
        if self.delete_auth_cookie:
            response.delete_cookie(settings.AUTH_COOKIE_NAME)
            self.delete_auth_cookie = False

        if self.refresh_login_timeout:
            response.set_signed_cookie(
                key=settings.ACCOUNTS_ENFORCE_LOGIN_COOKIE_NAME,
                value=now(),
                salt=settings.ACCOUNTS_ENFORCE_LOGIN_SALT
            )
            self.refresh_login_timeout = False

        return response
