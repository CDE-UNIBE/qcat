from django.test.utils import override_settings

from configuration.cache import get_configuration
from configuration.configuration import QuestionnaireConfiguration
from configuration.utils import create_new_code
from qcat.tests import TestCase
from questionnaire.serializers import QuestionnaireSerializer

from .test_models import get_valid_questionnaire


@override_settings(LANGUAGES=(
        ('en', 'English'), ('es', 'Spanish'), ('fr', 'French')))
class SerializerTest(TestCase):

    fixtures = ['sample.json', 'sample_global_key_values.json']

    def setUp(self):
        self.questionnaire = get_valid_questionnaire()
        linked_questionnaire = get_valid_questionnaire()
        linked_questionnaire.status = 4
        linked_questionnaire.save()
        self.questionnaire.add_link(linked_questionnaire)
        self.questionnaire.save()
        self.serialized = QuestionnaireSerializer(self.questionnaire).data  # noqa
        code = create_new_code(self.questionnaire, 'sample')
        linked_code = create_new_code(linked_questionnaire, 'sample')
        self.expected = {
            'original_locale': 'en',
            'flags': [],
            'code': code,
            'name': {'en': 'Unknown name'},
            'data': {'foo': 'bar'},
            'compilers': [{'name': 'bar foo', 'id': 1}],
            'list_data': {},
            'editors': [],
            'links': [
                {
                    'code': linked_code,
                    'configuration': 'sample',
                    'name': {
                        'default': 'Unknown name',
                        'en': 'Unknown name',
                        'fr': 'Unknown name',
                        'es': 'Unknown name',
                    },
                    'url': {
                        'default': '/en/sample/view/{}/'.format(linked_code),
                        'en': '/en/sample/view/{}/'.format(linked_code),
                        'fr': '/fr/sample/view/{}/'.format(linked_code),
                        'es': '/es/sample/view/{}/'.format(linked_code),
                    }
                }
            ],
            'url': '/en/sample/view/{}/'.format(code),
            'serializer_config': 'sample',
            'translations': ['en'],
            'status': ['draft', 'Draft'],
            'configurations': ['sample']
        }

    def test_init_with_config(self):
        configuration = QuestionnaireConfiguration(self.questionnaire.code)
        serializer = QuestionnaireSerializer(
            instance=self.questionnaire, config=configuration
        )
        self.assertEqual(serializer.config, configuration)

    def test_init_without_config(self):
        config = self.questionnaire.questionnaireconfiguration_set.filter(
            original_configuration=True
        ).first()
        original_config = get_configuration(config.configuration.code)

        serializer = QuestionnaireSerializer(
            instance=self.questionnaire
        )

        self.assertEqual(serializer.config.keyword, original_config.keyword)

    def test_get_links_serialize(self):
        self.assertListEqual(self.serialized['links'], self.questionnaire.links_property)

    def test_get_links_to_native(self):
        deserialized = QuestionnaireSerializer(data=self.serialized)
        self.assertTrue(deserialized.is_valid())
        self.assertListEqual(
            deserialized.validated_data['links'], self.questionnaire.links_property
        )

    def test_url(self):
        native = QuestionnaireSerializer(data=self.serialized)
        self.assertTrue(native.is_valid())
        self.assertEqual(
            self.questionnaire.get_absolute_url(), native.validated_data['url']
        )

    def test_complete_serialization(self):
        data = self.serialized
        # datetimes are not relevant to the structure.
        del data['created']
        del data['updated']

        self.assertDictEqual(data, self.expected)

    def test_complete_to_native(self):
        native = QuestionnaireSerializer(data=self.serialized)
        native.is_valid()

        # datetimes are not relevant to the structure.
        del native.validated_data['created']
        del native.validated_data['updated']

        self.assertEqual(native.validated_data, self.expected)
