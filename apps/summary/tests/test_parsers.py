from unittest.mock import patch, MagicMock, sentinel

from configuration.cache import get_configuration
from configuration.configuration import QuestionnaireQuestion
from qcat.tests import TestCase
from questionnaire.models import Questionnaire
from questionnaire.utils import get_questionnaire_data_in_single_language
from summary.parsers import QuestionnaireParser, TechnologyParser, \
    ApproachParser


class SummaryConfigurationTest(TestCase):
    """
    Tests for parsers.ConfiguredQuestionnaireSummary
    """

    def setUp(self):
        self.obj = QuestionnaireParser(
            config=MagicMock(),
            summary_type='full',
            questionnaire=MagicMock(),
            n_a=''
        )
        self.child = MagicMock(
            questiongroup=MagicMock(keyword='qg_keyword'),
            summary={'types': ['full'], 'default': {'field_name': 'spam'}}
        )

    def test_put_question_data_omit_unconfigured(self):
        self.assertIsNone(
            self.obj.put_question_data(MagicMock(in_summary={'half': ''}))
        )

    def test_put_questionnaire_field_name(self):
        child = MagicMock(
            questiongroup=MagicMock(keyword='qg_keyword'),
            summary={'types': ['full'],
                     'default':{'field_name': sentinel.field_name}}
        )
        self.obj.put_question_data(child=child)
        self.assertTrue(
            sentinel.field_name in self.obj.data
        )

    def test_put_questionnaire_multiple_field_names(self):
        child = MagicMock(
            keyword='keyword',
            questiongroup=MagicMock(keyword='qg_keyword'),
            summary={
                'types': ['full'],
                'default': {
                    'field_name': {'qg_keyword.keyword': sentinel.field_name}
                }
            }
        )
        self.obj.put_question_data(child=child)
        self.assertTrue(
            sentinel.field_name in self.obj.data
        )

    def test_put_questionnaire_override_function(self):
        child = MagicMock(
            questiongroup=MagicMock(keyword='qg_keyword'),
            summary={
                'types': ['full'],
                'default':
                    {'field_name': 'spam', 'get_value': {'name': 'foo'}}
            }
        )
        self.obj.foo = MagicMock()
        self.obj.put_question_data(child=child)
        self.obj.foo.assert_called_once_with(child=child)

    def test_put_questionnaire_override_function_config_type(self):
        child = MagicMock(
            questiongroup=MagicMock(keyword='qg_keyword'),
            summary={
                'types': ['full'],
                'default': {'field_name': 'spam', 'get_value': {'name': 'foo'}},
                'full': {'get_value': {'name': 'bar'}}
            }
        )
        self.obj.bar = MagicMock()
        self.obj.put_question_data(child=child)
        self.obj.bar.assert_called_once_with(child=child)

    def test_put_questionnaire_duplicate(self):
        self.obj.get_value = lambda child: sentinel.new_value
        self.obj.put_question_data(child=self.child)
        self.obj.data['spam'] = sentinel.existing_value
        self.assertEqual(
            self.obj.data, {'spam': sentinel.existing_value}
        )

    def test_put_questionnaire(self):
        self.obj.get_value = lambda child: sentinel.some_value
        self.obj.put_question_data(child=self.child)
        self.assertEqual(
            self.obj.data, {'spam': sentinel.some_value}
        )

    def test_get_map_values_no_geom(self):
        obj = QuestionnaireParser(
            config=MagicMock(),
            summary_type='full',
            questionnaire=MagicMock(geom=None),
            n_a=''
        )
        self.assertEqual(
            obj.get_map_values(''),
            {'img_url': '', 'coordinates': []}
        )

    @patch('summary.parsers.get_static_map_url')
    def test_get_map_values(self, mock_static_map):
        mock_static_map.return_value = sentinel.map_url
        obj = QuestionnaireParser(
            config=MagicMock(),
            summary_type='full',
            questionnaire=MagicMock(
                geom=MagicMock(coords=[(123.123456789, 456)])
            ),
            n_a=''
        )
        self.assertEqual(
            obj.get_map_values(''),
            {'img_url': sentinel.map_url, 'coordinates': ['123.12346, 456']}
        )

    def test_get_full_range_values(self):
        # choices as defined in child.choices
        all_choices = [
            ('pricey_key', 'pricey_value'),
            ('cheap_key', 'cheap_value'),
        ]
        self.obj.values['all_choices'] = [{'child_keyword': ['pricey_key']}]
        self.assertListEqual(
            [
                {'highlighted': True, 'text': 'pricey_value'},
                {'highlighted': False, 'text': 'cheap_value'}
            ],
            list(self.obj.get_full_range_values(
                child=MagicMock(
                    parent_object=MagicMock(keyword='all_choices'),
                    choices=all_choices,
                    keyword='child_keyword'
                )
            ))
        )


class ParserTestMixin:
    """
    Helpers for technology and approach parsers.
    """
    def get_child(self, qg_keyword: str, keyword: str) -> QuestionnaireQuestion:
        return QuestionnaireQuestion(
            self.config.get_questiongroup_by_keyword(qg_keyword),
            {'keyword': keyword}
        )


class TechnologyParserTest(ParserTestMixin, TestCase):
    """
    Combine all parts (config, questionnaire, parser), so no proper unit tests
    but more something like integration tests. These tests make sure that the
    parser still works after the config changes.
    Many 'real' functions are used instead of mocks, as setting up mocks for
    configs / children takes too much time. Also mocking would not result in
    more stable tests, as the exact structure of the config needed to be mocked.
    """
    fixtures = ['global_key_values', 'technologies', 'complete_questionnaires']

    def setUp(self):
        super().setUp()
        self.config = get_configuration('technologies')
        self.questionnaire = Questionnaire.objects.get(id=1)
        self.data = get_questionnaire_data_in_single_language(
            self.questionnaire.data, 'en'
        )
        self.parser = TechnologyParser(
            config=self.config,
            n_a='',
            questionnaire=self.questionnaire,
            summary_type='full',
            **self.data
        )

    def test_get_picto_and_nested_values(self):
        child = self.get_child('tech_qg_9', 'tech_landuse')
        values = list(self.parser.get_picto_and_nested_values(child))
        self.assertEquals(len(list(values)), 1)
        self.assertListEqual(
            list(values[0].keys()), ['url', 'title', 'text']
        )

    def test_get_impact(self):
        child = self.get_child('tech_qg_76', 'tech_impacts_cropproduction')
        values = list(
            self.parser.get_impact(child, has_siblings=True)
        )
        self.assertEqual(
            values[0],
            {
                'label': 'Crop production',
                'range': range(0, 7),
                'min': 'decreased',
                'max': 'increased',
                'selected': 4,
                'comment': ''
            }
        )

    def test_get_table(self):
        child = self.get_child('tech_qg_36', 'tech_input_est_specify')
        values = dict(self.parser.get_table(child))
        self.assertDictEqual(
            values['head'],
            {'0': 'Specify input', '1': 'Unit', '2': 'Quantity',
             '3': 'Costs per Unit', '4': 'Total costs per input',
             '5': '% of costs borne by land users'}
        )
        self.assertEqual(
            values['partials'][0]['head'], 'Labour'
        )
        self.assertDictEqual(
            list(values['partials'][0]['items'])[0],
            {
                '0': 'labour', '1': 'ha', '2': 1.0, '3': 2500.0, '4': 2500.0,
                '5': 100.0
            }
        )

    def test_get_climate_change(self):
        child = self.get_child('tech_qg_169', 'tech_exposure_incrdecr')
        values = list(self.parser.get_climate_change(child))
        self.assertEqual(
            values,
            [{'title': 'Gradual climate change', 'items': [{
                'label': 'seasonal temperature increase',
                'range': range(0, 5),
                'min': 'not well at all',
                'max': 'very well',
                'selected': None,
                'comment': 'Season: summer'
            }, {
                'label': 'annual rainfall decrease',
                'range': range(0, 5),
                'min': 'not well at all',
                'max': 'very well',
                'selected': None,
                'comment': ''}
            ]}]
        )


class ApproachParserTest(ParserTestMixin, TestCase):

    fixtures = ['global_key_values', 'approaches', 'complete_questionnaires']

    def setUp(self):
        super().setUp()
        self.config = get_configuration('approaches')
        self.questionnaire = Questionnaire.objects.get(id=2)
        self.data = get_questionnaire_data_in_single_language(
            self.questionnaire.data, 'en'
        )
        self.parser = ApproachParser(
            config=self.config,
            n_a='',
            questionnaire=self.questionnaire,
            summary_type='full',
            **self.data
        )

    def test_get_aims_enabling(self):
        child = self.get_child('app_qg_15', 'app_condition_enabling_specify')
        enabling = list(self.parser.get_aims_enabling(child, 'enabling'))
        self.assertEqual(
            enabling[0],
            'workload, availability of manpower: Enabling'
        )
        hindering = list(self.parser.get_aims_enabling(child, 'hindering'))
        self.assertEqual(
            hindering[0],
            'workload, availability of manpower: Hindering'
        )

    # def test_get_financing_subsidies(self):
    #     child = self.get_child('app_qg_27', 'app_subsidies_inputs')
    #     values = self.parser.get_financing_subsidies(child)

    def test_get_highlight_element(self):
        child = self.get_child('app_qg_105', 'app_financial_support')
        self.assertDictEqual(
            self.parser.get_highlight_element(child),
            {'highlighted': False, 'text': 'Monitoring and evaluation'}
        )

    def test_get_highlight_element_with_text(self):
        child = self.get_child('app_qg_22', 'app_institutions')
        values = dict(self.parser.get_highlight_element_with_text(child))
        self.assertListEqual(
            list(values['value']),
            [{'highlighted': False, 'text': 'no'},
             {'highlighted': False, 'text': 'yes, a little'},
             {'highlighted': True, 'text': 'yes, moderately'},
             {'highlighted': False, 'text': 'yes, greatly'}]
        )
        self.assertDictEqual(
            values['bool'],
            {'highlighted': True, 'text': 'Institution strengthening (organizational development)'}
        )

    def test_get_impacts(self):
        child = self.get_child('app_qg_39', 'app_impacts_empower_local_specify')
        values = list(self.parser.get_impacts(child))
        # cast values() to list for easy comparison.
        values[0]['scale'] = list(values[0]['scale'])
        self.assertListEqual(
            values,
            [{'label': 'Did the Approach enable evidence-based decision-making?',
              'range': range(0, 4), 'selected': 3, 'text': 'Water',
              'scale': ['No', 'Yes, little', 'Yes, moderately', 'Yes, greatly']
            }]
        )

    def test_get_impacts_motivation(self):
        child = self.get_child('app_qg_70', 'app_motivation')
        self.assertListEqual(
            list(self.parser.get_impacts_motivation(child)),
            [{'highlighted': False, 'text': 'increased production'},
             {'highlighted': False,
              'text': 'increased profit(ability), improved cost-benefit-ratio'},
             {'highlighted': False, 'text': 'reduced land degradation'},
             {'highlighted': True, 'text': 'reduced risk of disasters'},
             {'highlighted': False, 'text': 'reduced workload'},
             {'highlighted': False, 'text': 'payments/ subsidies'},
             {'highlighted': False,
              'text': 'rules and regulations (fines)/ enforcement'},
             {'highlighted': False,
              'text': 'prestige, social pressure/ social cohesion'},
             {'highlighted': False,
              'text': 'affiliation to movement/ project/ group/ networks'},
             {'highlighted': False, 'text': 'environmental consciousness'},
             {'highlighted': False, 'text': 'customs and beliefs, morals'},
             {'highlighted': False,
              'text': 'enhanced SLM knowledge and skills'},
             {'highlighted': False, 'text': 'aesthetic improvement'},
             {'highlighted': False, 'text': 'conflict mitigation'}]
        )

    def test_get_involvement(self):
        child = self.get_child('app_qg_113', 'app_involvement_type')
        values = list(self.parser.get_involvement(child))
        # check one element only, the exact number of elements is allowed to
        # vary.
        self.assertTrue(
            list(values[0].keys()), ['title', 'comments', 'items']
        )

    def test_get_stakeholders_roles(self):
        child = self.get_child('app_qg_100', 'app_stakeholders_roles')
        self.assertListEqual(
            list(self.parser.get_stakeholders_roles(child)),
            ['local land users/ local communities']
        )
