"""
All questionnaire data is on the elasticsearch-index. As of now, the database
is still touched. Efforts to refactor the following are in progress:

- Create new serializer (see stub: questionnaire.serializers)
- Use serializer when putting objects to the index
  (search.index.put_questionnaire_data)
- Put logic of 'get_list_values' to serializer.
- Put logic of new required fields for external API to serializer.
"""
import contextlib
from collections import OrderedDict

from django.conf import settings
from django.core.paginator import EmptyPage
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param, replace_query_param

from api.views import LogUserMixin, PermissionMixin
from questionnaire.models import Questionnaire
from questionnaire.view_utils import ESPagination, get_paginator, \
    get_page_parameter
from search.search import advanced_search
from ..utils import get_list_values


class QuestionnaireListView(PermissionMixin, LogUserMixin, GenericAPIView):
    """
    List view for questionnaires.

    Todo:
    - Refactor serializing / deserializing of indexed questionnaires
    - Add pagination
    - Add detail view
    - Improve docstrings

    """
    page_size = settings.API_PAGE_SIZE

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
        return list_values

    def get_es_paginated_results(self, offset):
        """
        Args:
            offset: int

        Returns:
            ESPagination

        """
        # Blank search returns all items within all indexes.
        es_search_results = advanced_search(
            limit=self.page_size,
            offset=offset
        )
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
            ('results', self.extend_results(data))
        ]))

    def extend_results(self, data):
        """
        Todo: refactor this. This hits the db for each element!
        Add the detail url to the results.

        Args:
            data: list of dictionaries.

        Returns:
            iterator
        """
        for questionnaire in data:
            with contextlib.suppress(Questionnaire.DoesNotExist):
                # Fetch db element and call the method to create the url.
                qs = Questionnaire.objects.get(id=questionnaire['id'])
                url = self.request.build_absolute_uri(qs.get_absolute_url())
                questionnaire.update({'url': url})
                yield questionnaire

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
