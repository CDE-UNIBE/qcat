from django.conf import settings
from elasticsearch import TransportError


def get_analyzer(language_code):
    """
    Return the analyzer value as specified in the settings under
    ``ES_ANALYZERS``.

    Args:
        ``language_code`` (str): The language code for the analyzer.

    Returns:
        ``str`` or ``None``. The name of the analyzer or ``None`` if not
        found or analyzers not specified.
    """
    try:
        return dict(settings.ES_ANALYZERS).get(language_code, None)
    except:
        return None


def get_alias(configuration_codes):
    """
    Return the alias of a configuration code. The alias is composed of
    the prefix as specified in the settings (``ES_INDEX_PREFIX``)
    followed by the ``configuration_code``.

    Args:
        ``configuration_codes`` (list). A list of configuration codes.
        If the list is empty, a wildcard is added to the prefix to
        search in all indices.

    Returns:
        ``str``. The composed alias.
    """
    if not configuration_codes:
        configuration_codes = ['*']
    return ','.join(['{}{}'.format(
        settings.ES_INDEX_PREFIX, c) for c in configuration_codes])


def check_connection(es, index=None):
    """
    Test if a connection to a given Elasticsearch instance is possible.

    If no index is provided, only an ``info`` query is executed to query
    the availability of the service.

    Args:
        ``es`` (elasticsearch.Elasticsearch): An Elasticsearch instance.

    Kwargs:
        ``index`` (str): If provided, the existance of the index is
        queried, returning ``False`` if it does not exist.

    Returns:
        ``bool``. A boolean indicating whether the connection was
        successful or the index exists.

        ``str``. An error message if available.
    """
    if index is None:
        try:
            es.info()
        except TransportError:
            return (
                False, 'Elasticsearch Error: No connection possible. Please '
                'check the configuration.')
        return True, ''

    try:
        index_exists = es.indices.exists(index=index)
    except TransportError:
        return (False, 'Elasticsearch Error: No connection possible. Please '
                'check the configuration.')
    if index_exists is not True:
        return (False, 'Elasticsearch Error: No index with name "{}" '
                'found'.format(index))
    return True, ''


def force_strings(serialized):
    """
    Recursively loop over values and cast lazy gettext objects to strings.

    Args:
        serialized: dict
    """
    for key, nested in serialized.items():
        if isinstance(nested, dict):
            serialized[key] = force_strings(nested)
        else:
            serialized[key] = str(nested)
    return serialized


def check_aliases(aliases):
    """
    Check if a list of strings contains only valid aliases.

    Args:
        aliases: A list of aliases to check.

    Returns:
        bool.
    """
    from search.search import get_indices_alias
    return set(aliases) <= set(get_indices_alias())
