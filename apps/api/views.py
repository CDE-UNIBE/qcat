import logging

from django.conf import settings

from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer, CoreJSONRenderer
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.schemas import SchemaGenerator
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer
from rest_framework import parsers, renderers
from rest_framework.throttling import UserRateThrottle

from api.models import AppToken
from api.authentication import AppTokenAuthentication
from .authentication import NoteTokenAuthentication
from api.serializers import AppTokenSerializer
from questionnaire.models import Questionnaire
from configuration.models import Configuration
from .models import EditRequestLog
from .models import RequestLog


logger = logging.getLogger(__name__)


class APIRoot(APIView):
    """
    Welcome to the API provided by WOCAT. This is a list with all endpoints
    that are available.

    This API is intended to be consumed by partners.

    Current version is: 2

    All available endpoints of the current API version are listed below. For an
    interactive documentation allowing to try out available requests visit the
    "documentation" endpoint below.

    Please contact the Wocat secretariat if you want to access the API, stating
    your activated Wocat account (required) and the purpose of your API requests.
    An authentication token will then be created for your account.

    More information on the API can be found in the [QCAT Documentation][doc].

    [doc]: https://qcat.readthedocs.io/en/latest/api/docs.html
    """
    http_method_names = ('get', )
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer)

    def get(self, request, format=None):
        identifier = Questionnaire.with_status.public().first().code
        configuration = Configuration.objects.latest('created')
        urls = {
            'configuration': reverse(
                'v2:api-configuration-structure',
                kwargs={
                    'code': configuration.code,
                    'edition': configuration.edition
                },
                request=request,
                format=format
            ),
            'configuration list': reverse(
                'v2:configuration-api-list',
                request=request,
                format=format
            ),
            'configuration edition list': reverse(
                'v2:configuration-edition-api-list',
                kwargs={
                    'code': configuration.code,
                },
                request=request,
                format=format
            ),
            'questionnaire list': reverse(
                'v2:questionnaires-api-list',
                request=request,
                format=format
            ),
            'questionnaire details': reverse(
                'v2:questionnaires-api-detail',
                kwargs={
                    'identifier': identifier
                },
                request=request,
                format=format
            ),

            'auth login': reverse(
                'v2:api-token-auth',
                request=request,
                format=format
            ),
            'questionnaire create': reverse(
                'v2:questionnaires-api-create',
                kwargs={
                    'configuration': configuration.code,
                    'edition': configuration.edition
                },
                request=request,
                format=format
            ),
            'questionnaire upload image': reverse(
                'v2:questionnaires-api-image-upload',
                request=request,
                format=format
            ),
            'questionnaire fetch edit': reverse(
                'v2:questionnaires-api-edit',
                kwargs={
                    'configuration': configuration.code,
                    'edition': configuration.edition,
                    'identifier': identifier
                },
                request=request,
                format=format
            ),
            'questionnaire edit': reverse(
                'v2:questionnaires-api-edit',
                kwargs={
                    'configuration': configuration.code,
                    'edition': configuration.edition,
                    'identifier': identifier
                },
                request=request,
                format=format
            ),
            'questionnaire my data': reverse(
                'v2:questionnaires-api-mydata',
                request=request,
                format=format
            ),

            'documentation': reverse(
                'api-docs',
                request=request,
                format=format
            ),
        }
        return Response(urls)


class SwaggerSchemaView(APIView):
    """
    The Swagger documentation of the *current* API version.
    """
    renderer_classes = [
        CoreJSONRenderer,
        OpenAPIRenderer,
        SwaggerUIRenderer,
    ]

    def get(self, request):
        # Define also the URL prefix for the current API version. Not very nice,
        # but did not find another way.
        generator = SchemaGenerator(
            title='QCAT API v2', url='/api/v2/', urlconf='api.urls.v2')
        schema = generator.get_schema(request=request, public=True)
        return Response(schema)


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


class LogEditAPIMixin:
    """

    """

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            EditRequestLog(user=request.user, resource=request.build_absolute_uri()).save()
        except Exception as e:
            logger.error(e)
        return super().finalize_response(request, response, *args, **kwargs)


class PermissionMixin:
    """
    Default permissions for all GET API views.

    """
    authentication_classes = (NoteTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        """
        Don't force permissions for development.
        """

        if settings.DEBUG:
            self.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
        return super().get_permissions()


class AppPermissionMixin:
    """
    Default permissions for all APP API views.

    """
    authentication_classes = (AppTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        """
        Don't force permissions for development.
        """

        if settings.DEBUG:
            self.permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
        return super().get_permissions()


class ObtainAuthToken(APIView):
    """
    Get application token for API v2.

    Returns the authenticated user's application token

    ``email``: The user's login email (e.g. "abc@domain.com").

    ``password``: The user's login password.
    """

    throttle_classes = (UserRateThrottle,)
    parser_classes = (parsers.FormParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = AppTokenSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = AppToken.objects.get_or_create(user=user)

        # Log this request, LogEditAPIMixin doesn't work as the user is not known
        try:
            EditRequestLog(user=user, resource=request.build_absolute_uri()).save()
        except Exception as e:
            # Catch any exception. Logging errors must not result in application errors.
            logger.error(e)

        return Response({'token': token.key})
