from unittest.mock import patch, MagicMock

from configuration.configuration import QuestionnaireQuestion
from configuration.configured_questionnaire import ConfiguredQuestionnaire
from qcat.tests import TestCase


class ConfiguredQuestionnaireTest(TestCase):

    @patch.object(ConfiguredQuestionnaire, 'put_question_data')
    def test_get_children_recursion(self, mock_put_question_data):
        child = MagicMock(spec=QuestionnaireQuestion, label='', keyword='')
        config = MagicMock(children=[child])
        ConfiguredQuestionnaire(config=config, questionnaire='')
        mock_put_question_data.assert_called_once_with(child)

    @patch.object(ConfiguredQuestionnaire, 'get_children')
    def test_get_value(self, mock_get_children):
        config = ConfiguredQuestionnaire(config='', questionnaire='')
        config.get_value(child=MagicMock(view_options={}))

    @patch.object(ConfiguredQuestionnaire, 'get_children')
    def test_active_child_in_store(self, mock_get_children):
        mock_get_children.return_value = None
        configured = ConfiguredQuestionnaire(config='', questionnaire='')
        configured.tmp_path = ['water', 'coffee']
        configured.store = {'water': {'coffee': {}}}
        configured.active_child_in_store['mate'] = {}
        self.assertDictEqual(
            configured.store,
            {'water': {'coffee': {'mate': {}}}}
        )

