from unittest.mock import patch, sentinel, MagicMock

from qcat.tests import TestCase
from summary.parsers import QuestionnaireParser
from summary.renderers import SummaryRenderer, GlobalValuesMixin


class SummaryDataProviderTest(TestCase):
    def test_summary_type(self):
        with self.assertRaises(NotImplementedError):
            SummaryRenderer(config='', questionnaire='', base_url='', quality='screen')

    @patch.object(QuestionnaireParser, '__init__')
    def test_content(self, mock_raw_data):
        mock_raw_data.return_value = {}
        with self.assertRaises(NotImplementedError):
            SummaryRenderer(
                config='', questionnaire='', base_url='', quality='screen'
            )


class GlobalValuesMixinTest(TestCase):

    def setUp(self):
        class Tmp(GlobalValuesMixin, SummaryRenderer):
            summary_type = 'type'
            content = ['sample']

            def sample(self):
                return sentinel.sample_value

        self.obj = Tmp(
            config=MagicMock(), questionnaire='', base_url='', quality='screen'
        )

    def test_raw_data_getter(self):
        # data as structured by the configured questionnaire summary
        self.obj.raw_data = {'key': [{'value': sentinel.expected}]}
        self.assertEqual(
            self.obj.raw_data_getter('key'),
            sentinel.expected
        )

    def test_raw_data_getter_custom_value(self):
        self.obj.raw_data = {'key': [{'value': sentinel.expected}]}
        self.assertEqual(
            self.obj.raw_data_getter('key', value=''),
            [{'value': sentinel.expected}]
        )

    def test_string_from_list(self):
        self.obj.raw_data = {'key': [{'values': ['will', 'i', 'am']}]}
        self.assertEqual(
            self.obj.string_from_list('key'),
            'will, i, am'
        )
