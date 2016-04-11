from functools import lru_cache

from django.conf import settings
from django.core.cache import cache
from django.db import ProgrammingError
from django.utils.translation import get_language

from .models import Configuration


def get_configuration(configuration_code):
    """
    Return a QuestionnaireConfiguration. If cache is being used (setting
    ``USE_CACHING=True``), it is returned from the cache if found. If
    not found, it is added to the cache and returned. If the use of
    cache is deactivated, always a new configuration is returned.

    Args:
        ``configuration_code`` (str): The code of the configuration

    Returns:
        ``QuestionnaireConfiguration``. The Questionnaire configuration,
        either returned from cache or newly created.
    """

    if False and settings.USE_CACHING:
        cache_key = get_cache_key(configuration_code)
        configuration = get_cached_configuration(
            cache_key,
            configuration_code
        )
        return configuration

    return get_configuration_by_code(configuration_code)


def get_total_configs():
    """
    Helper to set the maxsize for the lru_cache.
    """
    try:
        configs = Configuration.objects.filter(active=True).count()
    except ProgrammingError:
        # Except error: db does not exist yet.
        configs = 3

    languages = len(settings.LANGUAGES)
    total_configs = configs * languages
    # lru_cache works best if size is power of two.
    return 1 << (total_configs - 1).bit_length()


@lru_cache(maxsize=get_total_configs())
def get_cached_configuration(cache_key, configuration_code):
    """
    Simple retrieval. If object is not in the lru_cache, use the default cache
    from django as fallback.

    todo: discuss this - this doubles the required memory for cached
    configurations.
    """
    configuration = cache.get(cache_key)
    if not configuration:
        configuration = get_configuration_by_code(configuration_code)
        cache.set(key=cache_key, value=configuration)
    return configuration


def get_configuration_by_code(configuration_code):
    """
    Get the configuration object.
    """
    from configuration.configuration import QuestionnaireConfiguration
    return QuestionnaireConfiguration(configuration_code)


def delete_configuration_cache(configuration_object):
    """
    Delete a configuration object from the cache (incl. lru_cache) if it exists.

    Args:
        ``configuration_object`` (``QuestionnaireConfiguration``): The
        configuration object whose configuration is to be deleted.
    """

    cache_key = get_cache_key(configuration_object.code)

    if settings.USE_CACHING:
        cache.delete(cache_key)
        get_cached_configuration.cache_clear()


def get_cache_key(configuration_code):
    """
    Return the key under which a given configuration is stored in the
    cache. Currently, the key is composed as:
    ``[configuration_code]_[locale]``, for example ``technologies_en``.

    Args:
        ``configuration_code`` (str): The code of the configuration

    Returns:
        ``str``. The key for the cache.
    """
    return '{}_{}'.format(configuration_code, get_language())
