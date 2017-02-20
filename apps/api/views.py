import logging

from django.conf import settings
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .authentication import NoteTokenAuthentication
from .models import RequestLog, NoteToken
from .serializers import NoteAuthTokenSerializer

logger = logging.getLogger(__name__)


class APIRoot(APIView):
    """
    Welcome to the API provided by WOCAT. This is a list with all endpoints
    that are available.

    This API is intended to be consumed by partners.

    Current version is: 2
    """
    http_method_names = ('get', )
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer, )

    def get(self, request, format=None):
        urls = {
            'questionnaires': reverse('v2:questionnaires-api-list',
                                      request=request, format=format),
            'auth token': reverse('v2:obtain-api-token', request=request,
                                  format=format),
            'documentation': reverse('api-docs', request=request, format=format),
        }
        return Response(urls)


class ObtainNoteAuthTokenView(ObtainAuthToken):
    """
    Create a token for given user. Also saves a 'note' that is passed to the
    serializer.
    """
    serializer_class = NoteAuthTokenSerializer
    throttle_classes = (AnonRateThrottle, )

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = NoteToken.objects.get_or_create(
            user=user, defaults={'notes': serializer.validated_data['notes']}
        )
        if not created:
            token.notes = serializer.validated_data['notes']
            token.save()
        return Response({'token': token.key})


class LogUserMixin:
    """
    Log requests that access the API to the database, so usage statistics can
    be created.

    """
    # deactivated after issues during testing from skbp.
    # throttle_classes = (UserRateThrottle, )

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            RequestLog(
                user=request.user,
                resource=request.build_absolute_uri()
            ).save()
        # Catch any exception. Logging errors must not result in application
        # errors.
        except Exception as e:
            logger.error(e)
        return super().finalize_response(request, response, *args, **kwargs)


class PermissionMixin:
    """
    Default permissions for all API views.

    """
    authentication_classes = (NoteTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get_permissions(self):
        """
        Don't force permissions for development.
        """
        if settings.DEBUG:
            self.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
        return super().get_permissions()
