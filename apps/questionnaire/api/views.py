from collections import OrderedDict
import logging

from django.core.paginator import EmptyPage
from django.http import Http404
from django.utils.functional import cached_property
from django.utils.translation import get_language
from elasticsearch import TransportError
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.utils.urls import remove_query_param, replace_query_param

from api.views import LogUserMixin, PermissionMixin
from configuration.cache import get_configuration
from configuration.configured_questionnaire import ConfiguredQuestionnaire
from search.search import advanced_search, get_element
from ..conf import settings
from ..models import Questionnaire
from ..serializers import QuestionnaireSerializer
from ..utils import get_list_values, get_questionnaire_data_in_single_language
from ..view_utils import ESPagination, get_paginator, get_page_parameter


logger = logging.getLogger(__name__)


class QuestionnaireAPIMixin(PermissionMixin, LogUserMixin, GenericAPIView):
    """
    Shared functionality for list and detail view.
    """
    add_detail_url = False

    @cached_property
    def setting_keys(self):
        return set(settings.QUESTIONNAIRE_API_CHANGE_KEYS.keys())

    def update_dict_keys(self, items):
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
        for item in items:
            yield self.replace_keys(item)

    def language_text_mapping(self, **item) -> dict:
        """
        The consumers of the API require the text values in the format:
        {
            'language': 'en',
            'text': 'my text'
        }
        """
        return [{'language': key, 'text': value} for key, value in item.items()]

    def replace_keys(self, item):
        """
        Replace all keys as defined by the configuration. Also, list all
        translated versions. This was requested by the consumers of the API.
        To access description and name in all versions, the config must be
        loaded again.
        """
        matching_keys = self.setting_keys.intersection(item.keys())
        config = get_configuration(item['serializer_config'])
        if matching_keys:
            for key in matching_keys:
                definition = self.language_text_mapping(
                    **config.get_questionnaire_description(item['data'], key)
                )
                del item[key]
                item[settings.QUESTIONNAIRE_API_CHANGE_KEYS[key]] = definition

        # Special case: 'name' must include all translations.
        if item.get('name'):
            item['name'] = self.language_text_mapping(
                **config.get_questionnaire_name(item['data'])
            )

        if self.add_detail_url:
            item['api_url'] = reverse(
                '{api_version}:questionnaires-api-detail'.format(
                    api_version=self.request.version
                ),
                kwargs={'identifier': item['code']}
            )
        return item

    def filter_dict(self, items):
        """
        Starting with API v2 only name and url to the detail page are displayed.
        """
        for item in items:
            yield {
                'name': item.get('name'),
                'updated': item.get('updated'),
                'code': item.get('code'),
                'url': item.get('url'),
                'details': reverse(
                    '{api_version}:questionnaires-api-detail'.format(
                        api_version=self.request.version
                    ), kwargs={'identifier': item['code']}
                ),
            }


class QuestionnaireListView(QuestionnaireAPIMixin):
    """
    List view for questionnaires.

    """
    page_size = settings.API_PAGE_SIZE
    add_detail_url = True

    def get(self, request, *args, **kwargs):
        items = self.get_elasticsearch_items()
        return self.get_paginated_response(items)

    def get_elasticsearch_items(self):
        """
        Don't touch the database, but fetch everything from elasticsearch.

        Args:
            page: int For pagination: start at this position
            code: string Code of the questionnaire

        Returns:
            list of questionnaires
        """
        self.current_page = get_page_parameter(self.request)
        offset = self.current_page * self.page_size - self.page_size

        es_pagination = self.get_es_paginated_results(offset)

        questionnaires, self.pagination = get_paginator(
            es_pagination, self.current_page, self.page_size
        )

        # Combine configuration and questionnaire values.
        list_values = get_list_values(es_hits=questionnaires)
        if self.request.version == 'v1':
            return self.update_dict_keys(list_values)
        else:
            return self.filter_dict(list_values)

    def get_es_paginated_results(self, offset):
        """
        Args:
            offset: int

        Returns:
            ESPagination

        """
        try:
            # Blank search returns all items within all indexes.
            es_search_results = advanced_search(
                limit=self.page_size, offset=offset
            )
        except TransportError:
            # See https://redmine.cde.unibe.ch/issues/1098
            es_search_results = advanced_search(limit=0)
            total = es_search_results.get('hits', {}).get('total', 0)
            # If the page is not within the valid total return an empty response
            if total < offset:
                logger.warn('Potential issue from skbp: Invalid API request '
                            'with offset {}.'.format(offset))
                es_search_results = {}
            else:
                # There really are more results than ES pagination is originally
                # built for. Can be fixed by enabling deep pagination or such.
                raise

        # Build a custom paginator.
        es_hits = es_search_results.get('hits', {})
        return ESPagination(es_hits.get('hits', []), es_hits.get('total', 0))

    def get_paginated_response(self, data):
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

    def _get_paginate_link(self, page_number):
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

    def get_next_link(self):
        return self._get_paginate_link(self.current_page + 1)

    def get_previous_link(self):
        return self._get_paginate_link(self.current_page - 1)


class QuestionnaireDetailView(QuestionnaireAPIMixin):
    """
    Return a single item from elasticsearch, if object is still valid on the
    model.
    """
    add_detail_url = False

    def get(self, request, *args, **kwargs):
        item = self.get_elasticsearch_item()
        serialized = self.serialize_item(item)
        return Response(self.replace_keys(serialized))

    def get_elasticsearch_item(self):
        """
        Get a single element from elasticsearch. As the _id used for
        elasticsearch is the actual objects id, and not the
        code, resolve the id first.

        Returns: dict

        """
        self.obj = self.get_current_object()
        item = get_element(
            self.obj.id,
            self.obj.configurations.all().first().code
        )
        if not item:
            raise Http404()

        return item

    def serialize_item(self, item):
        """
        Serialize the data and get the list values -- the same as executed
        within advanced_search (get_list_values) in the QuestionnaireListView.
        """
        serializer = QuestionnaireSerializer(data=item)

        if serializer.is_valid():
            return self.prepare_data(serializer)
        else:
            logger.warning('Invalid data on the serializer: {}'.format(
                serializer.errors)
            )
            raise Http404()

    def prepare_data(self, serializer):
        serializer.to_list_values(lang=get_language())
        return serializer.validated_data

    def get_current_object(self):
        """
        Check if the model entry is still valid.

        Returns: object (Questionnaire instance)

        """
        return get_object_or_404(
            Questionnaire.with_status.public(), code=self.kwargs['identifier']
        )


class ConfiguredQuestionnaireDetailView(QuestionnaireDetailView):
    """
    Restore the fully configured questionnaires data.
    """

    def prepare_data(self, serializer: QuestionnaireSerializer) -> dict:
        """
        Merge configuration keyword, label and questionnaire data to a dict.
        """
        data = get_questionnaire_data_in_single_language(
            questionnaire_data=serializer.validated_data['data'],
            locale=get_language(),
            original_locale=serializer.validated_data['original_locale']
        )
        configured_questionnaire = ConfiguredQuestionnaire(
            config=serializer.config,
            questionnaire=self.obj,
            **data
        )
        return configured_questionnaire.store

    def get(self, request, *args, **kwargs):
        item = self.get_elasticsearch_item()
        serialized = self.serialize_item(item)
        return Response(serialized)
