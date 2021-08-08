from django import template
from urllib.parse import urlsplit, urlunsplit
from django.utils.translation import get_language_from_path

register = template.Library()


@register.filter
def clean_url(url):
    parsed = urlsplit(url)
    try:
        parts = parsed.path.split('/')
    except:
        return url
    lang = get_language_from_path(parsed.path)
    if len(parts) > 1 and parts[1] == lang:
        del parts[1]
    return urlunsplit((
        parsed.scheme, parsed.netloc, '/'.join(parts), parsed.query,
        parsed.fragment))
