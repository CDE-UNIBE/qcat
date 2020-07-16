from rest_framework.authentication import TokenAuthentication

from .models import NoteToken
from .models import AppToken

from datetime import timedelta
from datetime import datetime
import datetime as dtime
import pytz
from rest_framework import exceptions


class NoteTokenAuthentication(TokenAuthentication):
    """Use our custom model for the token auth for GET requests"""
    model = NoteToken


class AppTokenAuthentication(TokenAuthentication):
    """
    Use a custom model to authenticate POST requests
     - Expire and remove the token if not used in 24 hours
    """

    def authenticate_credentials(self, key):
        model = AppToken
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        # This is required for the time comparison
        utc_now = datetime.now(dtime.timezone.utc)
        utc_now = utc_now.replace(tzinfo=pytz.utc)

        # Check if the token has been used in the last 24 hours
        # - if not, delete the token and ask user to login to fetch a new token
        # - otherwise, update the updated time to now
        if token.updated < utc_now - timedelta(hours=24):
            token.delete()
            raise exceptions.AuthenticationFailed('APP Token expired, request a new APP Token')
        else:
            token.updated = utc_now
            token.save()

        return token.user, token
