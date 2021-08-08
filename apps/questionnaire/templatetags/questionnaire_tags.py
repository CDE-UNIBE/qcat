import warnings

from django import template
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer

from ..models import Questionnaire
from ..upload import get_url_by_file_name
from ..utils import get_link_display

register = template.Library()


@register.simple_tag
def get_static_map_url(obj):
    """
    Get the URL of the static map of a questionnaire.

    Args:
        obj: questionnaire.models.Questionnaire

    Returns:
        string: The URL or ''.
    """
    if isinstance(obj, Questionnaire):
        filename = '{}_{}.jpg'.format(obj.uuid, obj.version)
        return get_url_by_file_name(filename, subfolder='maps')
    return ''


@register.simple_tag
def call_model_method(method, obj, user):
    """
    Call a method on the Questionnaire model with given user and return its
    result.

    Args:
        method: string (method to call)
        obj: questionnaire.models.Questionnaire
        user: accounts.User

    Returns:
        string: result of the called function

    """
    if isinstance(obj, Questionnaire):
        result = getattr(obj, method)(user)
        return result if not isinstance(result, tuple) else result[1]
    return ''


def replace_large(interchange, url):
    """
    Replace the 'large' image with the url of the cropped image.
    """
    for text in interchange:
        if text.endswith('(large)]'):
            yield '[{}, (large)]'.format(url)
        else:
            yield text


def get_percent(base, value):
    return float(value) / base * 100


@register.simple_tag
def prepare_image(image):
    """
    Helper to display the main image, with a focus point as set in the form.

    Args:
        image: dict

    Returns:
        dict

    """
    # The aspect ratio is optimized for nn screens. This should be set to match
    # the box with the default screen resolution (according to piwik).
    size = (1800, 900)

    if image.get('absolute_path') and image.get('target'):
        # Create a thumbnailer instance (file-like object) and create its
        # thumbnail according to the options.
        # Return the thumbnails url and overwrite the interchange-dict.
        try:
            thumbnailer = get_thumbnailer(
                image['absolute_path']
            ).get_thumbnail({
                'size': size,
                'crop': size,
                'upscale': True,
                'target': image['target']
            })
            url = get_url_by_file_name(thumbnailer.name.rsplit('/')[-1])
            interchange = list(replace_large(image.get('interchange'), url))
        except InvalidImageFormatError:
            interchange = image.get('interchange')
            url = image.get('image')

    else:
        interchange = image.get('interchange')
        url = image.get('image')

    return {
        'interchange': ','.join(interchange) if isinstance(interchange, list) else interchange,
        'src': url
    }


@register.simple_tag
def link_display(configuration_code, name, identifier):
    return get_link_display(configuration_code, name, identifier)


@register.filter
def keyvalue(dict, key):
    return dict.get(key)


@register.filter
def is_editor(roles: list) -> bool:
    """
    From the 'roles' list with tuples, check if 'editor' is one of the roles.
    """
    return any([role[0] == 'editor' for role in roles])


@register.filter
def get_flat_roles(roles: list) -> list:
    """
    Return a flat list of role keywords present in the current roles.
    """
    return [role[0] for role in roles]


@register.filter
def is_in_compilers_list(user, compilers):
    return user.is_authenticated() and user.id in [compiler['id'] for compiler in compilers]
