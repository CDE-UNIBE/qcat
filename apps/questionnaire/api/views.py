from collections import OrderedDict
import logging

from django.core.paginator import EmptyPage
from django.http import Http404
from django.utils.translation import get_language
from django.shortcuts import get_list_or_404
from django.db.models import Q
from django.utils import timezone

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.utils.urls import remove_query_param, replace_query_param
from rest_framework.mixins import CreateModelMixin
from rest_framework import status

from PIL import Image

from questionnaire.serializers import QuestionnaireInputSerializer
from questionnaire.utils import validate_questionnaire_data, is_valid_questionnaire_format, compare_questionnaire_data
from configuration.structure import ConfigurationStructure
from api.views import LogEditAPIMixin, AppPermissionMixin
from configuration.cache import get_configuration
from api.views import LogUserMixin, PermissionMixin
from configuration.configured_questionnaire import ConfiguredQuestionnaire
from questionnaire.views import ESQuestionnaireQueryMixin
from search.search import get_element
from ..conf import settings
from ..models import Questionnaire, APIEditRequests, File
from ..utils import get_list_values, get_questionnaire_data_in_single_language


logger = logging.getLogger(__name__)


class QuestionnaireAPIMixin(PermissionMixin, LogUserMixin, GenericAPIView):
    """
    Shared functionality for list and detail view.
    """
    add_detail_url = False

    def update_dict_keys(self, es_hits: list):
        """
        Some keys need to be updated (e.g. description has a different key
        depending on the config) for a more consistent behavior of the APIs
        data.
        This cannot be done when indexing (elasticsearch) the data, as the
        templates expect the variable names in the 'original' format.
        After discussion with the people consuming the api, the language of
        the content is used as key, i.e.: 'unccd_description': 'a title' becomes
        'definition: {'en': 'a title'}
        """
        for es_hit in es_hits:
            yield self.replace_keys(es_hit)

    def language_text_mapping(self, **item) -> list:
        """
        The consumers of the API require the text values in the format:
        {
            'language': 'en',
            'text': 'my text'
        }
        """
        return [{'language': key, 'text': value} for key, value in item.items()]

    def replace_keys(self, es_hit: dict) -> dict:
        """
        Replace all keys as defined by the configuration. Also, list all
        translated versions. This was requested by the consumers of the API.
        To access description and name in all versions, the config must be
        loaded again.
        """
        try:
            list_values = get_list_values(es_hits=[es_hit])[0]
        except IndexError:
            # We want to know about these errors.
            raise Exception('Possibly invalid data in ES (unable to serialize)'
                            ': %s' % es_hit)

        # 'name' and 'definition' must include all translations.
        list_values['name'] = es_hit['_source']['list_data']['name']
        list_values['definition'] = es_hit['_source']['list_data']['definition']

        # Restore state of configuration for v1.
        list_values['configurations'] = [list_values['configuration']]
        list_values['native_configuration'] = True

        # Remove keys that are not available on v1.
        delete_keys = ['serializer_config', 'serializer_edition', 'has_new_configuration_edition']
        for key in delete_keys:
            del list_values[key]

        # Add 'full' data, even for the list view.
        list_values['data'] = self.get_object_data(code=list_values['code'])

        if self.add_detail_url:
            list_values['api_url'] = reverse(
                '{api_version}:questionnaires-api-detail'.format(
                    api_version=self.request.version
                ),
                kwargs={'identifier': list_values['code']}
            )

        return list_values

    def get_object_data(self, code: str) -> dict:
        obj = self.object if hasattr(self, 'object') else self.get_current_object(code=code)
        return obj.data

    def filter_dict(self, items: dict):
        """
        Starting with API v2 only name and url to the detail page are displayed.
        """
        for item in items:
            yield {
                'name': item.get('name'),
                'updated': item.get('updated'),
                'code': item.get('code'),
                'edition': item.get('serializer_edition'),
                'url': reverse(
                    viewname='{configuration}:questionnaire_details'.format(
                        configuration=item['configuration']
                    ),
                    kwargs={'identifier': item['code']}),
                'translations': item.get('translations'),
                'details': reverse(
                    '{api_version}:questionnaires-api-detail'.format(
                        api_version=self.request.version
                    ), kwargs={'identifier': item['code']}
                ),
            }

    def get_current_object(self, code='') -> Questionnaire:
        """
        Check if the model entry is still valid.

        Returns: object (Questionnaire instance)
        """
        return get_object_or_404(
            Questionnaire.with_status.public(), code=self.kwargs.get('identifier', code)
        )


class QuestionnaireListView(QuestionnaireAPIMixin, ESQuestionnaireQueryMixin):
    """
    Get a list of Questionnaires, for v1 and v2

    Return a list of Questionnaires. The same filter parameters as for the list
    view (search/filter in QCAT) can be passed.

    ``page``: Optional page offset.
    """
    page_size = settings.API_PAGE_SIZE
    add_detail_url = True
    configuration_code = 'wocat'

    def get(self, request, *args, **kwargs) -> Response:
        self.set_attributes()
        items = self.get_elasticsearch_items()
        return self.get_paginated_response(items)

    def get_elasticsearch_items(self):
        """
        Don't touch the database, but fetch everything from elasticsearch.

        Returns:
            list of questionnaires
        """
        es_results = self.get_es_results(call_from='api')

        es_pagination = self.get_es_paginated_results(es_results)
        questionnaires, self.pagination = self.get_es_pagination(es_pagination)

        # Combine configuration and questionnaire values.
        if self.request.version == 'v1':
            return self.update_dict_keys(es_hits=questionnaires)
        else:
            return self.filter_dict(
                get_list_values(es_hits=questionnaires)
            )

    def get_paginated_response(self, data) -> Response:
        """
        Build a response as if it were from the django rest framework. This
        will be replaced after the refactor.

        Args:
            data: dict The data which is returned

        Returns:
            Response

        """
        return Response(OrderedDict([
            ('count', self.pagination.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', list(data))
        ]))

    def _get_paginate_link(self, page_number) -> str:
        """
        Args:
            page_number: int

        Returns:
            string: URL of the requested page

        """
        try:
            self.pagination.validate_number(page_number)
        except EmptyPage:
            return ''

        url = self.request.build_absolute_uri()
        if page_number == 1:
            return remove_query_param(url, 'page')
        return replace_query_param(url, 'page', page_number)

    def get_next_link(self) -> str:
        return self._get_paginate_link(self.current_page + 1)

    def get_previous_link(self)  -> str:
        return self._get_paginate_link(self.current_page - 1)


class QuestionnaireDetailView(QuestionnaireAPIMixin):
    """
    Return a single item from elasticsearch, if object is still valid on the
    model.

    Used for API v1 only
    """
    add_detail_url = False

    def get(self, request, *args, **kwargs):
        """
        Set the current object to 'self', so the query is not executed again
        in the method 'replace_keys'.
        """
        self.object = self.get_current_object()
        # Get the single element from ES.
        es_hit = get_element(questionnaire=self.object)
        if not es_hit:
            raise Http404

        return Response(self.replace_keys(es_hit={'_source': es_hit}))


class ConfiguredQuestionnaireDetailView(QuestionnaireDetailView):
    """
    Get a single Questionnaire for API v2.

    Return a single Questionnaire by its code. The returned data contains the
    full configuration (including labels of sections, questiongroups etc.).

    ``identifier``: The identifier / code of the questionnaire.
    """

    def prepare_data(self) -> dict:
        """
        Merge configuration keyword, label and questionnaire data to a dict.
        """
        data = get_questionnaire_data_in_single_language(
            questionnaire_data=self.object.data,
            locale=get_language(),
            original_locale=self.object.original_locale
        )
        # Links are removed from the 'data' dict, but available on the
        # serialized element.
        data['links'] = self.prepare_link_data(
            *self.object.links_property
        )
        return data

    @staticmethod
    def prepare_link_data(*links):
        """
        Get data in current language; see: Questionnaire.links_property
        """
        translate_fields = ['name', 'url']
        for link in links:
            for field in translate_fields:
                link[field] = link[field].get(get_language(), link[field]['default'])
        return links

    def get_configured_questionnaire(self, **data):
        return ConfiguredQuestionnaire(
            config=self.object.configuration_object,
            questionnaire=self.object,
            **data
        ).store

    def get(self, request, *args, **kwargs):
        self.object = self.get_current_object()
        prepared_data = self.prepare_data()
        return Response(self.get_configured_questionnaire(**prepared_data))


class QuestionnaireCreateNew(CreateModelMixin, AppPermissionMixin, LogEditAPIMixin, GenericAPIView):
    """
    Create a new questionnaire for API v2

    Returns the  identifier of the newly created Questionnaire.
    The POST data must contain questiongroup keywords and its values

    ``configuration``: The code of the configuration (e.g. "technologies").

    ``edition``: The edition of the configuration (e.g. "2018").
    """

    serializer_class = QuestionnaireInputSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
        }

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)
#
    def post(self, request, *args, **kwargs):

        if not request.data:
            # No data passed.
            return Response({'detail': 'No questionnaire data.'}, status=status.HTTP_400_BAD_REQUEST)

        # Parse the configuration code and edition
        request_code = kwargs['configuration']
        request_edition = kwargs['edition']

        # Validate configuration exists for code and edition
        structure_obj = ConfigurationStructure(code=request_code, edition=request_edition,)

        if structure_obj.error:
            # No configuration found for this code and edition.
            return Response({'detail': 'No configuration found for this code and edition.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Fetch a new configuration
        request_config = get_configuration(code=request_code, edition=request_edition)

        # Questionnaires can only be created for the latest edition
        if request_config.has_new_edition:
            # Newer edition found for this code
            return Response({'detail': 'A newer edition exists for {}. Questionnaires can be '
                                       'published only for the latest edition.'.format(request_code)},
                            status=status.HTTP_400_BAD_REQUEST)

        # Questionnaire data is validated
        cleaned_data, config_errors = validate_questionnaire_data(request.data, request_config)

        if config_errors:
            # Questionnaire data does not fit configuration structure.
            return Response({'detail': config_errors}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the questionnaire data using the serializer
        serializer = self.get_serializer(data={'data': cleaned_data})
        if serializer.is_valid():

            # Create a new Questionnaire and save
            new_questionnaire = Questionnaire.create_new(
                configuration_code=request_code,
                data=cleaned_data,
                user=request.user,
                created=timezone.now(),
                updated=timezone.now()
            )
            new_questionnaire.save()

            return Response({'success': "true",
                             'code': new_questionnaire.code},
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# TODO: Maybe use a common mixin class for initial validation across get and post
class QuestionnaireEdit(AppPermissionMixin, LogEditAPIMixin, GenericAPIView):
    """
        Get or Edit a single questionnaire for API v2
    """

    serializer_class = QuestionnaireInputSerializer

    def get(self, request, *args, **kwargs):
        """
        Get a Questionnaire by its identifier for API v2.

        Returns the questiongroup keywords and its values

        ``configuration``: The code of the configuration (e.g. "technologies").

        ``edition``: The edition of the configuration (e.g. "2018").

        ``identifier``: The identifier / code of the questionnaire (e.g. technologies_0123).
        """

        # Parse the configuration code, edition and idenfiier
        request_code = kwargs['configuration']
        request_edition = kwargs['edition']
        request_identifier = kwargs['identifier']

        # Validate configuration exists for code and edition
        structure_obj = ConfigurationStructure(code=request_code, edition=request_edition, )

        if structure_obj.error:
            # No configuration found for this code and edition.
            return Response({'detail': 'No configuration found for this configuration code and edition.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Fetch all questionnaire versions for the identifier
        questionnaire_all = get_list_or_404(Questionnaire.with_status.not_deleted(), code=request_identifier)
        # questionnaire = Questionnaire.with_status.not_deleted().filter(code=request_identifier).latest('version')

        # Use the latest version of the questionnaire if more than one version exists
        questionnaire = sorted(questionnaire_all, key=lambda x: x.version, reverse=True)[0]
        if questionnaire is None:
            # No questionnaire exists or is deleted
            # - this is a redundant check...
            raise Http404()

        # Check configuration matches
        if not questionnaire.configuration_object == get_configuration(code=request_code, edition=request_edition):
            # Configuration mismatch
            return Response({'detail': 'Questionnaire does not match configuration code and edition.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Get request user's role in this questionnaire
        request_user_role = ''
        for user_role, user in questionnaire.get_users():
            if user == request.user:
                request_user_role = user_role
                break

        if not request_user_role:
            # User has no role on this questionnaire
            return Response({'detail': 'Unauthorized.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check the questionnaire status, allow access only when DRAFT/PUBLIC
        if questionnaire.status not in (settings.QUESTIONNAIRE_DRAFT, settings.QUESTIONNAIRE_PUBLIC):
            # Questionnaire is not editable
            return Response({'detail': 'Not editable.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        # Check if the questionnaire has any locks
        if not questionnaire.can_edit(user=request.user):
            # Questionnaire is currently locked for editing
            blocked_msg = questionnaire.get_blocked_message(user=request.user)[1]
            return Response({'detail': blocked_msg}, status=status.HTTP_409_CONFLICT)

        # Handle the EditRequests table entry
        # - This request could also be to just view the data, nonetheless we record it as an Edit Request
        # - Check if the same user has an active EditRequest for this Questionnaire
        #   - if Yes, access timestamp and questionnaire version are updated
        #   - if No, Create a new EditRequest
        if APIEditRequests.with_status.is_active(code=request_identifier, for_user=request.user):
            # Found an active request from the user, updating
            APIEditRequests.objects.filter(
                questionnaire_code=request_identifier,
                user=request.user,
                is_edit_complete=False
            ).update(
                access=timezone.now(),
                questionnaire_version=questionnaire.version
            )
        else:
            # No active request from the user, creating
            APIEditRequests.objects.create(
                questionnaire_code=request_identifier,
                questionnaire_version=questionnaire.version,
                user=request.user)

        # Finally, deserialize the questionnaire data
        serializer = QuestionnaireInputSerializer(questionnaire)

        return Response({'status': questionnaire.status_property[0],
                         'data': serializer.data['data']},
                        status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Update a Questionnaire by its identifier for API v2.

        Returns the  identifier of the updated Questionnaire.
        The POST data must only contain questiongroup keywords and its values

        ``configuration``: The code of the configuration (e.g. "technologies").

        ``edition``: The edition of the configuration (e.g. "2018").

        ``identifier``: The identifier / code of the questionnaire (e.g. technologies_0123).
        """

        if not request.data:
            # No data passed.
            return Response({'detail': 'No questionnaire data.'}, status=status.HTTP_400_BAD_REQUEST)

        # Parse the configuration code, edition and idenfiier
        request_code = kwargs['configuration']
        request_edition = kwargs['edition']
        request_identifier = kwargs['identifier']

        # Validate configuration exists for code and edition
        structure_obj = ConfigurationStructure(code=request_code, edition=request_edition, )

        if structure_obj.error:
            # No configuration found for this code and edition.
            return Response({'detail': 'No configuration found for this configuration code and edition.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # APIEditRequest corresponding to POST, when the user made the GET, must exist
        if not APIEditRequests.with_status.is_active(code=request_identifier, for_user=request.user):
            # No matching edit request, edit is rejected
            return Response({'detail': 'Must fetch questionnaire data before submitting edits.'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

        # Fetch all questionnaire versions for the identifier
        questionnaire_all = get_list_or_404(Questionnaire.with_status.not_deleted(), code=request_identifier)
        # questionnaire = Questionnaire.with_status.not_deleted().filter(code=request_identifier).latest('version')

        # Use the latest version of the questionnaire if more than one version exists
        questionnaire = sorted(questionnaire_all, key=lambda x: x.version, reverse=True)[0]
        if questionnaire is None:
            # No questionnaire exists or is deleted
            # - this is a redundant check...
            raise Http404()

        # Fetch a the configuration
        request_config = get_configuration(code=request_code, edition=request_edition)

        # Questionnaires can only be created for the latest edition
        if request_config.has_new_edition:
            # Newer edition found for this code
            err = str(
                'A newer edition exists for {}. Questionnaires can be published only for the latest edition.'.format(
                    request_code))
            return Response({'detail': err}, status=status.HTTP_406_NOT_ACCEPTABLE)

        # Check configuration matches
        if questionnaire.configuration_object != request_config:
            # Configuration mismatch
            return Response({'detail': 'Questionnaire does not match configuration code and edition.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Get request user's role in this questionnaire
        request_user_role = ''
        for user_role, user in questionnaire.get_users():
            if user == request.user:
                request_user_role = user_role
                break

        if not request_user_role:
            # User has no role on this questionnaire
            return Response({'detail': 'Unauthorized.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check the questionnaire status, allow access only when DRAFT/PUBLIC
        if questionnaire.status not in (settings.QUESTIONNAIRE_DRAFT, settings.QUESTIONNAIRE_PUBLIC):
            # Questionnaire is not editable
            return Response({'detail': 'Not editable.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        # Get the EditRequest created for the GET request
        questionnaire_edit_request = get_object_or_404(APIEditRequests.with_status.is_active(
            code=request_identifier, for_user=request.user))

        # An active request found from the user
        # - Validate the version and timestamps
        if not questionnaire_edit_request.questionnaire_version == questionnaire.version:
            # Newer questionnaire version exists, user has to GET again
            return Response({'detail': 'Newer Questionnaire version available.'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

        if not questionnaire_edit_request.access > questionnaire.updated:
            # Questionnaire updated, user has to GET again
            return Response({'detail': 'Questionnaire updated since edit started.'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)

        # Validate the questionnaire edit data
        cleaned_data, config_errors = validate_questionnaire_data(request.data, request_config)

        if config_errors:
            # Questionnaire data does not fit configuration structure.
            return Response({'detail': config_errors}, status=status.HTTP_400_BAD_REQUEST)

        if not compare_questionnaire_data(cleaned_data, questionnaire.data):
            # No changes to Questionnaire data
            return Response({'detail': "No changes detected."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the questionnaire edit data using the serializer
        serializer = self.get_serializer(data={'data': cleaned_data})
        if serializer.is_valid():

            # Edit Request is set to complete
            questionnaire_edit_request.close_request(is_edit_complete=True)

            # Questionnaire data is updated
            questionnaire.update_data(serializer.data['data'], timezone.now(), questionnaire.configuration.code)

            return Response({'success': "true",
                             'code': questionnaire.code},
                            status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuestionnaireImageUpload(AppPermissionMixin, LogEditAPIMixin, APIView):
    """
    Upload image files for a questionnaire for API v2

    Returns the identifier, url and thumbnails of the newly created Image.

    The image data must be of content-type: multipart/form-data
    """

    parser_classes = (MultiPartParser, FormParser,)
    throttle_classes = (UserRateThrottle,)

    def post(self, request, format=None, *args, **kwargs):

        if 'file' not in request.data:
            return Response({'detail': 'Empty content'}, status=status.HTTP_400_BAD_REQUEST)

        file_data = request.data['file']

        # Checking if uploaded blob is an image
        try:
            img = Image.open(file_data)
            img.verify()
        except Exception as ex:
            print(str(ex))
            return Response({'detail': 'Not an image file'}, status=status.HTTP_400_BAD_REQUEST)

        # Uploaded file is stored and thumbnails are generated
        # - unsupported file types <only png, jpg and gif are allowed>
        # - max. file size allowed is 3MB
        try:
            file_obj = File.handle_upload(file_data)
        except Exception as ex:
            return Response({'detail': str(ex)}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the stored file and return the id, thumbnails & url
        file_data = File.get_data(file_object=file_obj)
        ret = {
            'success': True,
            'uid': file_data.get('uid'),
            'interchange': file_data.get('interchange'),
            'url': file_data.get('url'),
        }

        return Response(ret, status=status.HTTP_201_CREATED)


class QuestionnaireMyData(AppPermissionMixin, LogEditAPIMixin, GenericAPIView):
    """
        Get a list of Questionnaires, where the User is the Compiler
    """

    def get(self, request, *args, **kwargs):
        """
            Get a list of Questionnaires where the user is the compiler.
        """

        # Questionnaires where their status is draft/public and the request.user is the compiler
        status_filter = (
                Q(members=request.user) &
                Q(questionnairemembership__role__in=[
                    settings.QUESTIONNAIRE_COMPILER
                ])
                & Q(status__in=[settings.QUESTIONNAIRE_DRAFT,
                                settings.QUESTIONNAIRE_PUBLIC
                                ])
        )

        # All the public/draft questionnaires for the request.user are fetched
        query = Questionnaire.with_status.not_deleted()\
            .filter(status_filter)\
            .order_by('code', '-updated') \
            .distinct('code')

        if len(query) == 0:
            # No questionnaires for this user
            return Response({'details': 'No questionnaires created.'}, status=status.HTTP_404_NOT_FOUND)

        # Array for accumulating the questionnaires
        list_entries = []

        for obj in query:
            # For each questionnaire following attributes are fetched
            # - name
            # - image location
            # - short description
            # - created datetime
            # - updated datetime
            # - code
            # - edition
            # - status <draft|public>

            # Metadata from the configuration template is fetched
            questionnaire_data = obj.configuration_object.get_list_data([obj.data])[0]

            # Country & code specific definition/description fields are removed
            # - Only name, image path & short definition are appended
            if 'country' in questionnaire_data:
                del questionnaire_data['country']
                
            dict_keys = list(questionnaire_data.keys())
            for key in dict_keys:
                if key.endswith('_definition') or key.endswith('_description'):
                    del questionnaire_data[key]

            # Metadata is fetched and appended
            questionnaire_data.update(obj.get_metadata())

            # Questionnaire edition is added
            if 'configuration' in questionnaire_data:
                questionnaire_data.update({'edition': questionnaire_data['configuration'].edition})

            # Extra attributes are removed
            if 'status' in questionnaire_data:
                del questionnaire_data['status']

            if 'compilers' in questionnaire_data:
                del questionnaire_data['compilers']

            if 'reviewers' in questionnaire_data:
                del questionnaire_data['reviewers']

            if 'editors' in questionnaire_data:
                del questionnaire_data['editors']

            if 'configuration' in questionnaire_data:
                del questionnaire_data['configuration']

            if 'translations' in questionnaire_data:
                del questionnaire_data['translations']

            if 'flags' in questionnaire_data:
                del questionnaire_data['flags']

            if 'original_locale' in questionnaire_data:
                del questionnaire_data['original_locale']

            # Status attribute is added as a string and the last attribute
            questionnaire_data.update({'status': obj.get_status_display().lower()})

            # Questionnaire is added to array
            list_entries.append(questionnaire_data)

        return Response({'results': list_entries}, status=status.HTTP_200_OK)
