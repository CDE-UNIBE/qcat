import collections
from django.conf import settings
from elasticsearch import TransportError

from .index import get_elasticsearch
from .utils import get_alias


es = get_elasticsearch()


def simple_search(query_string, configuration_codes=[]):
    """
    Perform a simple full text search based on a query string.

    https://www.elastic.co/guide/en/elasticsearch/reference/1.6/search-search.html

    Args:
        ``query_string`` (str): The query string to be provided as ``q``
        parameter.

    Kwargs:
        ``configuration_codes`` (list): An optional list of
        configuration codes to limit the search to certain indices.

    Returns:
        ``dict``. The search results as returned by
        ``elasticsearch.Elasticsearch.search``.
    """
    alias = get_alias(configuration_codes)
    return es.search(index=alias, q=get_escaped_string(query_string))


def get_es_query(
        filter_params: list=None, query_string: str='',
        match_all: bool=True) -> dict:
    """
    Kwargs:
        ``filter_params`` (list): A list of filter parameters. Each
        parameter is a tuple consisting of the following elements:

            [0]: questiongroup

            [1]: key

            [2]: values (list)

            [3]: operator

            [4]: type (eg. checkbox / text)

        ``query_string`` (str): A query string for the full text search.

        ``match_all`` (bool): Whether the query MUST match all filters or not.
        If not all filters must be matched, the results are ordered by relevance
        to show hits matching more filters at the top. Defaults to False.

    Returns:
        ``dict``. A dictionary containing the query to be passed to ES.
    """
    if filter_params is None:
        filter_params = []

    es_queries = []

    def _get_query_string(qg, k, v):
        return {
            'query_string': {
                'query': v,
                'fields': [f'data.{qg}.{k}']
            }
        }

    # Filter parameters: Nested subqueries to access the correct
    # questiongroup.
    for filter_param in list(filter_params):

        if filter_param.type in [
                'checkbox', 'image_checkbox', 'select_type', 'select_model',
                'radio', 'bool']:

            # So far, range operators only works with one filter value. Does it
            # even make sense to have multiple of these joined by OR with the
            # same operator?
            if filter_param.operator in ['gt', 'gte', 'lt', 'lte']:
                query = {
                    'range': {
                        f'data.{questiongroup}.{key}_order': {
                            filter_param.operator: filter_param.values[0]
                        }
                    }
                }
            else:
                if len(filter_param.values) > 1:
                    query_strings = [
                        _get_query_string(filter_param.questiongroup,
                                          filter_param.key, v) for v in
                        filter_param.values]
                    query = {
                        'bool': {
                            'should': query_strings
                        }
                    }
                else:
                    query = _get_query_string(
                        filter_param.questiongroup, filter_param.key,
                        filter_param.values[0])

            es_queries.append({
                'nested': {
                    'path': f'data.{filter_param.questiongroup}',
                    'query': query
                }
            })

        elif filter_param.type in ['text', 'char']:
            es_queries.append({
                "nested": {
                    "path": "data.{}".format(filter_param.questiongroup),
                    "query": {
                        "multi_match": {
                            "query": filter_param.values[0],
                            "fields": ["data.{}.{}.*".format(
                                filter_param.questiongroup, filter_param.key)],
                            "type": "most_fields",
                        }
                    }
                }
            })

        elif filter_param.type in ['_date']:
            years = filter_param.values[0].split('-')
            if len(years) != 2:
                continue
            es_queries.append({
                'range': {
                    filter_param.key: {
                        'from': '{}||/y'.format(years[0]),
                        'to': '{}||/y'.format(years[1]),
                    }
                }
            })

        elif filter_param.type in ['_flag']:
            es_queries.append({
                'nested': {
                    'path': 'flags',
                    'query': {
                        'query_string': {
                            'query': filter_param.values[0],
                            'fields': ['flags.flag'],
                        }
                    }
                }
            })

    if query_string:
        es_queries.append({
            "query_string": {
                "query": get_escaped_string(query_string)
            }
        })

    es_bool = 'must' if match_all is True else 'should'

    return {
        "query": {
            "bool": {
                es_bool: es_queries
            }
        },
        "sort": [
            "_score",
            {
                "updated": "desc"
            }
        ]
    }


def get_aggs_query(filter_params: list) -> dict:
    """
    Return a query which contains aggregations for all values of the currently
    active filters.

    Args:
        filter_params: A list of FilterParam tuples.

    Returns:
        dict.
    """
    def _get_agg(qg, k):
        return {
            'nested': {
                'path': f'data.{qg}'
            },
            'aggs': {
                'values': {
                    'terms': {
                        'field': f'data.{qg}.{k}'
                    }
                }
            }
        }

    aggs = {}
    for f in filter_params:
        aggs[f'{f.questiongroup}__{f.key}'] = _get_agg(f.questiongroup, f.key)

    return {
        'aggs': aggs,
    }


def advanced_search(
        filter_params: list=None, query_string: str='',
        configuration_codes: list=None, limit: int=10,
        offset: int=0, match_all: bool=True,
        include_buckets: bool=False) -> dict:
    """
    Kwargs:
        ``filter_params`` (list): A list of filter parameters. Each
        parameter is a tuple consisting of the following elements:

            [0]: questiongroup

            [1]: key

            [2]: values (list)

            [3]: operator

            [4]: type (eg. checkbox / text)

        ``query_string`` (str): A query string for the full text search.

        ``configuration_codes`` (list): An optional list of
        configuration codes to limit the search to certain indices.

        ``limit`` (int): A limit of query results to return.

        ``offset`` (int): The number of query results to skip.

        ``match_all`` (bool): Whether the query MUST match all filters or not.
        If not all filters must be matched, the results are ordered by relevance
        to show hits matching more filters at the top. Defaults to False.

    Returns:
        ``dict``. The search results as returned by
        ``elasticsearch.Elasticsearch.search``.
    """
    query = get_es_query(
        filter_params=filter_params, query_string=query_string,
        match_all=match_all)

    if include_buckets is True:
        query.update(get_aggs_query(filter_params))

    alias = get_alias(configuration_codes)
    return es.search(index=alias, body=query, size=limit, from_=offset)


def get_values_count(
        questiongroup, key, filter_params: list=None, query_string: str='',
        configuration_codes: list=None, match_all: bool=True) -> dict:
    """
    Return a dict containing the values of the question along with the count of
    how many results there are in ES for every value.
    """
    query = get_es_query(
        filter_params=filter_params, query_string=query_string,
        match_all=match_all)

    MockFilterParam = collections.namedtuple(
        'MockFilterParam', ['questiongroup', 'key'])
    query.update(get_aggs_query([MockFilterParam(questiongroup, key)]))
    query.update({
        'size': 0,  # Do not include the actual hits
    })

    alias = get_alias(configuration_codes)
    es_query = es.search(index=alias, body=query)

    buckets = es_query.get('aggregations', {}).get(
        f'{questiongroup}__{key}', {}).get('values', {}).get('buckets', [])

    return {b['key']: b['doc_count'] for b in buckets}


def get_element(object_id: int, *configuration_codes) -> dict:
    """
    Get a single element from elasticsearch.
    """
    alias = get_alias(configuration_codes)
    try:
        return es.get_source(index=alias, id=object_id, doc_type='questionnaire')
    except TransportError:
        return {}


def get_escaped_string(query_string: str) -> str:
    """
    Replace all reserved characters when searching the ES index.
    """
    for char in settings.ES_QUERY_RESERVED_CHARS:
        query_string = query_string.replace(char, '\\{}'.format(char))
    return query_string


def get_indices_alias():
    """
    Return a list of all elasticsearch index aliases. Only ES indices which
    start with the QCAT prefix are respected.

    Returns:
        list.
    """
    indices = []
    for aliases in es.indices.get_aliases().values():
        for alias in aliases.get('aliases', {}).keys():
            if settings.ES_INDEX_PREFIX not in alias:
                continue
            indices.append(alias.replace(settings.ES_INDEX_PREFIX, ''))
    return indices
