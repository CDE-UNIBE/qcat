import contextlib
import logging
import random

import requests
from django.conf import settings
from django.db import models

from requests.exceptions import RequestException
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class RequestLog(models.Model):
    """
    Simple model to log requests to the API.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    access = models.DateTimeField(auto_now_add=True)
    resource = models.CharField(max_length=100)

    class Meta:
        ordering = ['access']

    def __str__(self):
        return u"{}: {}".format(self.user, self.resource)

    def submit_to_piwik(self):
        """
        Try to call piwiks API after a new requestlog was created. No fancy error handling though; this is not an
        important feature.
        """
        if settings.PIWIK_SITE_ID and settings.PIWIK_URL and settings.PIWIK_AUTH_TOKEN:
            # List of all attributes: http://developer.piwik.org/api-reference/tracking-api
            with contextlib.suppress(RequestException):
                response = requests.post(
                    '{}piwik.php'.format(settings.PIWIK_URL), data={
                        'idsite': settings.PIWIK_SITE_ID,
                        'rec': '1',  # fixed value according to API docs
                        'url': self.resource,
                        'action_name': 'API',
                        '_id': self.user_id,
                        'rand': random.random(),
                        'apiv': settings.PIWIK_API_VERSION,  # only version 1 available as of now
                        'token_auth': settings.PIWIK_AUTH_TOKEN,
                        'uid': self.user.email
                    }
                )
                if not response.ok:
                    logger.error(
                        'Error submitting API requests to piwik: {r.content} '
                        '(status: {r.status_code})'.format(r=response))


class NoteToken(Token):
    """
    Provide info about usage of a token. This is required for statistics of the
    API and its usage.
    """
    notes = models.TextField()

    @property
    def requests_from_user(self):
        return self.user.requestlog_set.count()
