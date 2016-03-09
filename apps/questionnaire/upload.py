import magic
import os
import sys
import subprocess
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import ugettext as _
from uuid import uuid4


UPLOAD_THUMBNAIL_EXTENSION = 'jpg'
UPLOAD_THUMBNAIL_CONTENT_TYPE = 'image/jpeg'


def create_thumbnails(file_path, content_type):
    """
    Create thumbnails for a file found under a given path. The thumbnails are
    stored and the identifiers returned in a dictionaries with their format.

    Parameters taken from http://stackoverflow.com/a/7262050/841644

    Args:
        file_path: The path of the original file.

        content_type: The content type of the file.

    Returns:
        dict. A dictionary where each key is a thumbnail format and the value
        the identifier of the respective thumbnail file.
    """
    quality = '85%'

    thumbnails = {}
    for format_name, format_settings in settings.UPLOAD_IMAGE_THUMBNAIL_FORMATS:
        uid = str(uuid4())

        resize_format = '{}x{}'.format(format_settings[0], format_settings[1])

        folder_path = get_upload_folder_path(uid)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        thumbnail_path = os.path.join(
            folder_path, '{}.{}'.format(uid, UPLOAD_THUMBNAIL_EXTENSION))

        if content_type == 'application/pdf':
            params = '-density 300 -background white -alpha remove'
        else:
            params = '-strip -interlace Plane -sampling-factor 4:2:0'

        cmd = 'convert -quality {quality} -resize {size} {params} ' \
              '{input}[0] {output}'.format(quality=quality, size=resize_format,
                                           params=params, input=file_path,
                                           output=thumbnail_path)
        subprocess.call(cmd, shell=True)

        thumbnails[format_name] = uid

    return thumbnails


def store_file(file):
    """
    This function handles the actual storage of an uploaded file after
    checking it.

    Args:
        file (django.core.files.uploadedfile.UploadedFile or
        Buffer).

    Returns:
        str. The uuid of stored file.

        str. The path of the file.
    """
    if isinstance(file, UploadedFile):
        content_type = file.content_type
        size = file.size
    else:
        content_type = magic.from_buffer(file, mime=True).decode('utf-8')
        size = sys.getsizeof(file)

    file_extension = get_file_extension_by_content_type(content_type)
    if file_extension is None:
        raise Exception(_('Unsupported file type'))

    if size > settings.UPLOAD_MAX_FILE_SIZE:
        raise Exception(_('File is too big'))

    upload_folder = settings.MEDIA_ROOT
    uid = str(uuid4())
    filename = '{}.{}'.format(uid, file_extension)
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    upload_path = os.path.join(
        upload_folder, *get_upload_folder_structure(uid))
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    file_path = os.path.join(upload_path, filename)
    with open(file_path, 'wb+') as destination:
        if isinstance(file, UploadedFile):
            for chunk in file.chunks():
                destination.write(chunk)
        else:
            destination.write(file)
    return uid, file_path


def get_upload_folder_path(uid):
    """
    Return the path of the upload folder of a given file.

    Args:
        uid (str): The identifier of the file.

    Returns:
        str. The path of the file in its upload folder.
    """
    upload_folder = settings.MEDIA_ROOT
    return os.path.join(upload_folder, *get_upload_folder_structure(uid))


def get_file_path(file_object, thumbnail=None):
    """
    Return the path and name of a file.

    Args:
        file_object (questionnaire.models.File): A file model instance.

        thumbnail (str): The thumbnail format or None.

    Returns:
        str. The path of the file in its upload folder.

        str. The name of the file.
    """
    file_extension = get_file_extension_by_content_type(
        file_object.content_type)
    uid = file_object.uuid
    if thumbnail is not None:
        file_extension = UPLOAD_THUMBNAIL_EXTENSION
        uid = file_object.thumbnails.get(thumbnail)
        if uid is None:
            return None, None

    file_name = '{}.{}'.format(uid, file_extension)
    upload_path = get_upload_folder_path(uid)
    file_path = os.path.join(upload_path, file_name)
    return file_path, file_name


def retrieve_file(file_object, thumbnail=None):
    """
    Read and return a file.

    Args:
        file_object (:mod:`questionnaire.models.File`). A file object.

        thumbnail (str): The name of the thumbnail format if
        available.

    Returns:
        ``Buffer``, ``str``. The file object read into memory and the
        filename of the file.
    """
    file_path, file_name = get_file_path(file_object, thumbnail=thumbnail)
    return open(file_path, 'rb'), file_name


def get_all_file_extensions():
    """
    Return all file extensions which are valid according to the
    setting ``UPLOAD_VALID_FILES``.

    .. seealso::
        Configuration of ``UPLOAD_VALID_FILES`` in
        :doc:`/configuration/settings`

    Returns:
        ``list``. A list of tuples with the content type and extension.
        Example::

          [
            ('image/jpeg', 'jpg'),
            ('application/pdf', 'pdf')
          ]

    Raises:
        ``Exception``. If setting ``UPLOAD_VALID_FILES`` is not set or
        not correctly formatted.
    """
    try:
        valid_files = settings.UPLOAD_VALID_FILES
        ret = []
        for content_type, extensions in valid_files.items():
            ret.extend(extensions)
        return ret
    except:
        raise Exception(
            'Setting "UPLOAD_VALID_FILES" is not set or not valid. Please '
            'consult the documentation.')


def get_file_extension_by_content_type(content_type):
    """
    Return the file extension for a given content_type. Based on the
    setting ``UPLOAD_VALID_FILES``.

    .. seealso::
        Configuration of ``UPLOAD_VALID_FILES`` in
        :doc:`/configuration/settings`

    Args:
        content_type (str): The content type to find the file
        extension for.

    Returns:
        str or None. The file extension for the given content type. None if the
        content type was not found.
    """
    file_extension = [
        v[1] for v in get_all_file_extensions() if v[0] == content_type]
    if len(file_extension) != 1:
        return None
    return file_extension[0]


def get_url_by_file_name(file_name):
    """
    Return the relative URL of a file based on its filename. The URL
    basically indicates the location where the file was stored in the
    upload folder.

    .. important::
        It is not verified if the file at the given location actually
        exists.

    Args:
        file_name (str): The full filename of the file.

    Returns:
        str. The relative URL of the file.
    """
    folder_path = os.path.join(*get_upload_folder_structure(file_name))
    return os.path.join(settings.MEDIA_URL, folder_path, file_name)


def get_upload_folder_structure(file_name):
    """
    Return the structure in the upload folder used for storing and
    retrieving uploaded files.

    Two folder levels are created based on the filename (UUID). The
    first level consists of the first two characters, the second level
    consists of the third character of the uuid.

    Example: ``9cd7b281-2c70-42eb-86ec-e29fc755cc1e.jpg`` is stored to
    ``9c/d/9cd7b281-2c70-42eb-86ec-e29fc755cc1e.jpg``.

    Args:
        file_name (str): The name of the file.

    Returns:
        list. A list of the folders or an empty list if there was a problem with
        the file name.
    """
    try:
        return [file_name[0:2], file_name[2:3]]
    except TypeError:
        return []
