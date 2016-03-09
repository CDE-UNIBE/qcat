from django.conf import settings
from django.db import models

from rest_framework.authtoken.models import Token


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


class NoteToken(Token):
    """
    Provide info about usage of a token. This is required for statistics of the
    API and its usage.
    """
    notes = models.TextField()

    @property
    def requests_from_user(self):
        return self.user.requestlog_set.count()
