import functools
import hashlib

from django import template
from django.contrib.staticfiles import finders

register = template.Library()


@register.simple_tag
def summary_css_hash():
    """
    Manual cache-busting for summary css, as wkhtmltopdf only works with full
    urls, but django-compressor only works with files in COMPRESS_URLS.
    """
    summary_css_path = finders.find('css/summary.css')
    with open(summary_css_path, 'rb') as f:
        d = hashlib.md5()
        for buf in iter(functools.partial(f.read, 128), b''):
            d.update(buf)
    return d.hexdigest()
