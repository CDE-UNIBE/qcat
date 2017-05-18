from django.contrib.auth.backends import ModelBackend
from .client import typo3_client


class WocatAuthenticationBackend(ModelBackend):
    """
    The class to handle the authentication through :term:`WOCAT`.
    """

    def authenticate(self, username=None, password=None, **kwargs):
        """
        Custom authentication. Returns a user if authentication
        successful.

        The basic workflow is:
        - post username and password into the actual form on the wocat.net site
        - if credentials are valid, a cookie is returned
        - with given cookie, the user_id from wocat.net (typo3) can be resolved
        - with the user_id, the user data can be accessed.

        If any of these steps fail, the authentication fails. Improved exception
        handling will be implemented if requested (should be done, but no time
        is assigned for this task).

        Args:
            password:
            username:

        """
        # Login the user on the remote system.
        session_id = typo3_client.remote_login(username, password)
        if not session_id:
            return None

        user_id = typo3_client.get_user_id(session_id)
        if not user_id:
            return None

        # Get django user and update data from the api.
        user = typo3_client.get_and_update_django_user(user_id, session_id)

        # TODO: Handle privileges and permissions
        return user


class WocatCMSAuthenticationBackend(ModelBackend):
    """
    Authentication against new (2017) wocat website.
    """

    def authenticate(self, username=None, password=None, **kwargs):
        """
        Custom authentication. Returns a user if authentication
        successful.
        """
        user_data = typo3_client.remote_login(username, password)
        if not user_data:
            return None

        return typo3_client.get_and_update_django_user(**user_data)
