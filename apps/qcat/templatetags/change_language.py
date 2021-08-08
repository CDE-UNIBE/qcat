from django.conf import settings
from django.template import Library
from django.urls  import resolve, reverse, Resolver404
from django.utils.translation import activate, get_language

register = Library()


@register.simple_tag(takes_context=True)
def change_lang(context, lang=None, *args, **kwargs):
    """
    From https://djangosnippets.org/snippets/2875/
    Get active page's url by a specified language
    Usage: {% change_lang 'en' %}
    """
    path = context['request'].path
    try:
        url_parts = resolve(path)
    except Resolver404:
        return path

    url = path
    cur_language = get_language()
    try:
        activate(lang)
        url = reverse(url_parts.view_name, kwargs=url_parts.kwargs)
    finally:
        activate(cur_language)

    return "%s" % url


@register.filter
def get_full_language_name(locale: str) -> str:
    """
    Return the full name of a language by its locale.
    """
    return dict(settings.LANGUAGES).get(locale, locale)
