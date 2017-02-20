from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, Mock

from qcat.tests import TestCase
from questionnaire.upload import (
    get_all_file_extensions,
    get_file_extension_by_content_type,
    create_thumbnails,
    get_upload_folder_structure,
    get_url_by_file_name,
    retrieve_file,
    store_file,
)
from questionnaire.tests.test_views import valid_file

TEST_UPLOAD_IMAGE_THUMBNAIL_FORMATS = (
    ('default', (640, 480)),
    ('small', (1024, 768)),
    ('medium', (1440, 1080)),
)

TEST_UPLOAD_VALID_FILES = {
    'image': (
        ('image/jpeg', 'jpg'),
        ('image/png', 'png'),
    ),
    'document': (
        ('application/pdf', 'pdf'),
    )
}


@override_settings(
    UPLOAD_IMAGE_THUMBNAIL_FORMATS=TEST_UPLOAD_IMAGE_THUMBNAIL_FORMATS)
@patch('questionnaire.upload.os')
class CreateThumbnailsTest(TestCase):

    @patch('questionnaire.upload.subprocess')
    def test_calls_subprocess(self, mock_subprocess, mock_os):
        create_thumbnails('path', 'content_type')
        self.assertEqual(mock_subprocess.call.call_count, 3)


@patch('questionnaire.upload.os.makedirs')
class StoreFileTest(TestCase):

    @patch('questionnaire.upload.magic.from_buffer')
    def test_uses_magic_to_determine_content_type(self, mock_magic, mock_os):
        file = Mock()
        with self.assertRaises(Exception):
            store_file(file)
        mock_magic.assert_called_once_with(file, mime=True)

    @override_settings(UPLOAD_VALID_FILES=TEST_UPLOAD_VALID_FILES)
    @patch('questionnaire.upload.get_file_extension_by_content_type')
    def test_calls_get_file_extension_by_content_type(self, mock_func, mock_os):
        file = SimpleUploadedFile('img.png', open(valid_file, 'rb').read())
        file.content_type = 'image/png'
        store_file(file)
        mock_func.assert_called_once_with('image/png')

    @override_settings(UPLOAD_VALID_FILES=TEST_UPLOAD_VALID_FILES)
    def test_raises_exception_if_invalid_file_extension(self, mock_os):
        file = SimpleUploadedFile('img.png', open(valid_file, 'rb').read())
        file.content_type = 'foo'
        with self.assertRaises(Exception):
            store_file(file)

    @override_settings(UPLOAD_MAX_FILE_SIZE=1)
    @patch('questionnaire.upload.get_file_extension_by_content_type')
    @patch('questionnaire.upload.sys.getsizeof')
    @patch('questionnaire.upload.magic.from_buffer')
    def test_raises_exception_if_file_too_big(
            self, mock_from_buffer, mock_get_size_of, mock_get_file_extension,
            mock_os):
        mock_from_buffer.return_value = b''
        mock_get_size_of.return_value = 2
        mock_get_file_extension.return_value = 'some/filetype'
        file = Mock()
        with self.assertRaises(Exception):
            store_file(file)


@override_settings(UPLOAD_VALID_FILES=TEST_UPLOAD_VALID_FILES)
class RetrieveFileTest(TestCase):

    @patch('questionnaire.upload.get_file_extension_by_content_type')
    def test_calls_get_file_extension_by_content_type(self, mock_func):
        file = Mock()
        file.uuid = ''
        file.content_type = 'foo'
        with self.assertRaises(FileNotFoundError):
            retrieve_file(file)
        mock_func.assert_called_once_with('foo')

    @patch('questionnaire.upload.get_upload_folder_structure')
    def test_uses_thumbnail_if_provided(
            self, mock_get_upload_folder_structure):
        file = Mock()
        file.uuid = ''
        file.content_type = 'foo'
        file.thumbnails = {'bar': 'asdf'}
        with self.assertRaises(FileNotFoundError):
            retrieve_file(file, thumbnail='bar')
        mock_get_upload_folder_structure.assert_called_once_with('asdf')


@override_settings(UPLOAD_VALID_FILES=TEST_UPLOAD_VALID_FILES)
class GetAllFileExtensionsTest(TestCase):

    def test_returns_list(self):
        ext = get_all_file_extensions()
        self.assertIsInstance(ext, list)
        self.assertEqual(len(ext), 3)
        self.assertIn(('image/jpeg', 'jpg'), ext)
        self.assertIn(('image/png', 'png'), ext)
        self.assertIn(('application/pdf', 'pdf'), ext)

    @override_settings(UPLOAD_VALID_FILES=None)
    def test_handles_no_files(self):
        with self.assertRaises(Exception):
            get_all_file_extensions()


@override_settings(UPLOAD_VALID_FILES=TEST_UPLOAD_VALID_FILES)
class GetFileExtensionByContentTypeTest(TestCase):

    def test_returns_file_extension(self):
        ext = get_file_extension_by_content_type('image/png')
        self.assertEqual(ext, 'png')

    def test_returns_None_if_unknown_content_type(self):
        ext = get_file_extension_by_content_type('foo')
        self.assertIsNone(ext)


class GetUrlByFileNameTest(TestCase):

    @patch('questionnaire.upload.get_upload_folder_structure')
    def test_calls_get_upload_folder_structure(self, func):
        func.return_value = 'foo'
        get_url_by_file_name('foo.jpg')
        func.assert_called_once_with('foo.jpg')

    @override_settings(MEDIA_URL='/media/')
    @patch('questionnaire.upload.get_upload_folder_structure')
    def test_returns_url(self, mock_get_upload_folder_structure):
        mock_get_upload_folder_structure.return_value = 'a', 'b'
        url = get_url_by_file_name('foo.jpg')
        self.assertEqual(url, '/media/a/b/foo.jpg')


class GetUploadFolderStructureTest(TestCase):

    def test_returns_folders(self):
        folders = get_upload_folder_structure('filename')
        self.assertEqual(folders, ['fi', 'l'])

    def test_returns_empty_if_exception(self):
        self.assertEqual(get_upload_folder_structure(None), [])
