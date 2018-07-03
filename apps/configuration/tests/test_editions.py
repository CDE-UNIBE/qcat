from unittest import mock

from qcat.tests import TestCase
from configuration.models import Configuration, Key, Value, Translation
from ..editions.base import Edition, Operation


class EditionsTest(TestCase):

    @property
    def model_kwargs(self):
        return dict(
            key=mock.MagicMock(spec=Key),
            value=mock.MagicMock(spec=Value),
            configuration=mock.MagicMock(spec=Configuration),
            translation=mock.MagicMock(spec=Translation)
        )

    def get_edition(self, code='test_code', edition='1234'):

        class TestEdition(Edition):
            def __init__(self, code, edition, **kwargs):
                self.code = code
                self.edition = edition
                super().__init__(**kwargs)

        return TestEdition(
            code=code,
            edition=edition,
            **self.model_kwargs
        )

    def test_invalid_code(self):
        with self.assertRaises(AttributeError):
            self.get_edition()

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_no_operations(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]
        with self.assertRaises(NotImplementedError):
            self.get_edition().operations

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_update_translation(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        new_translation = {'label': 'bar'}
        edition = self.get_edition()
        translation_obj = mock.MagicMock()
        edition.translation.objects.get.return_value = translation_obj

        edition.update_translation(
            update_pk=1, **new_translation
        )
        self.assertIn(
            mock.call.data.update({'test_code_1234': new_translation}),
            translation_obj.method_calls
        )

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_create_translation(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        new_translation = {'label': 'bar'}
        edition = self.get_edition()

        edition.create_new_translation(
            translation_type='type', **new_translation)

        self.assertIn(
            mock.call.create(
                data={'test_code_1234': new_translation},
                translation_type='type'),
            edition.translation.objects.method_calls
        )

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_create_new_value_new_translation(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        edition = self.get_edition()

        translation = {'label': 'bar'}
        edition.create_new_value(keyword='keyword', translation=translation)

        # Creates translation
        self.assertIn(
            mock.call.create(
                data={'test_code_1234': translation},
                translation_type='value'),
            edition.translation.objects.method_calls
        )
        # Creates value
        self.assertIn(
            mock.call.create(
                configuration=None, keyword='keyword', order_value=None,
                translation=edition.translation.objects.create.return_value),
            edition.value.objects.method_calls
        )

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_create_new_value_existing_translation(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        edition = self.get_edition()

        config = {'some': 'config'}
        edition.create_new_value(
            keyword='keyword', translation=1, order_value=1,
            configuration=config)

        # Creates translation
        self.assertIn(
            mock.call.get(pk=1),
            edition.translation.objects.method_calls
        )
        # Creates value
        self.assertIn(
            mock.call.create(
                configuration=config, keyword='keyword', order_value=1,
                translation=edition.translation.objects.get.return_value),
            edition.value.objects.method_calls
        )

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_create_new_question(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        edition = self.get_edition()

        translation = {'label': 'bar'}
        edition.create_new_question(
            keyword='keyword', translation=translation, question_type='text')

        # Creates translation
        self.assertIn(
            mock.call.create(
                data={'test_code_1234': translation},
                translation_type='key'),
            edition.translation.objects.method_calls
        )
        # Creates value
        self.assertIn(
            mock.call.create(
                configuration={'type': 'text'}, keyword='keyword',
                translation=edition.translation.objects.create.return_value),
            edition.key.objects.method_calls
        )

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_find_in_data(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        edition = self.get_edition()

        data = {
            'sections': [
                {
                    'keyword': 'section_1',
                    'categories': [
                        {
                            'keyword': 'category_1',
                            'subcategories': [
                                {
                                    'keyword': 'subcat_1',
                                    'questiongroups': [
                                        {
                                            'keyword': 'qg_1',
                                            'questions': [
                                                {
                                                    'keyword': 'question_1',
                                                }
                                            ]
                                        },
                                        {
                                            'keyword': 'qg_2',
                                            'questions': [
                                                {
                                                    'keyword': 'question_2'
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'keyword': 'section_2',
                    'categories': [
                        {
                            'keyword': 'category_2'
                        }
                    ]
                }
            ]
        }

        self.assertEqual(
            edition.find_in_data(
                path=('section_2', 'category_2'),
                **data)['keyword'],
            'category_2')

        self.assertEqual(
            edition.find_in_data(
                path=('section_1', 'category_1', 'subcat_1', 'qg_2', 'question_2'),
                **data)['keyword'],
            'question_2')

        with self.assertRaises(KeyError):
            edition.find_in_data(path=('does', 'not', 'exist'), **data)

    @mock.patch.object(Configuration, 'CODE_CHOICES', new_callable=mock.PropertyMock)
    def test_update_data(self, mock_choices):
        mock_choices.return_value = [('test_code', 'test_code'), ]

        edition = self.get_edition()

        data = {
            'sections': [
                {
                    'keyword': 'section_1',
                    'categories': [
                        {
                            'keyword': 'category_1',
                            'subcategories': [
                                {
                                    'keyword': 'subcat_1',
                                    'questiongroups': [
                                        {
                                            'keyword': 'qg_1',
                                            'questions': [
                                                {
                                                    'keyword': 'question_1',
                                                }
                                            ]
                                        },
                                        {
                                            'keyword': 'qg_2',
                                            'questions': [
                                                {
                                                    'keyword': 'question_2'
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'keyword': 'section_2',
                    'categories': [
                        {
                            'keyword': 'category_2'
                        }
                    ]
                }
            ]
        }

        updated_value = {'keyword': 'category_2', 'foo': 'bar'}
        updated_data = edition.update_data(
            path=('section_2', 'category_2'), updated=updated_value, **data)
        self.assertEqual(
            edition.find_in_data(
                path=('section_2', 'category_2'),
                **updated_data)['foo'],
            'bar')


class OperationTest(TestCase):

    def test_update_questionnaire_data(self):
        mock_fn = mock.Mock()
        operation = Operation(
            transform_configuration='',
            release_note='',
            transform_questionnaire=mock_fn
        )
        data = {'foo': 'bar'}
        operation.update_questionnaire_data(**data)
        mock_fn.assert_called_once_with(**data)