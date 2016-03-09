from unittest.mock import Mock

from qcat.tests import TestCase
from qcat.utils import (
    clear_session_questionnaire,
    find_dict_in_list,
    is_empty_list_of_dicts,
    get_session_questionnaire,
    save_session_questionnaire,
)


class IsEmptyListOfDictsTest(TestCase):

    def test_returns_false_if_not_empty(self):
        is_empty = is_empty_list_of_dicts([{"foo": "bar"}])
        self.assertFalse(is_empty)

    def test_returns_true_if_empty(self):
        is_empty = is_empty_list_of_dicts([{"foo": ""}])
        self.assertTrue(is_empty)

    def test_returns_true_if_empty_with_None(self):
        is_empty = is_empty_list_of_dicts([{"foo": None}])
        self.assertTrue(is_empty)

    def test_returns_true_if_false_as_value(self):
        is_empty = is_empty_list_of_dicts([{"foo": False}])
        self.assertFalse(is_empty)

    def test_returns_true_if_empty_list(self):
        is_empty = is_empty_list_of_dicts([{"foo": []}])
        self.assertTrue(is_empty)

    def test_returns_False_if_not_empty_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": "bar"}}])
        self.assertFalse(is_empty)

    def test_returns_true_if_empty_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": ""}}])
        self.assertTrue(is_empty)

    def test_returns_true_if_None_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": None}}])
        self.assertTrue(is_empty)

    def test_returns_true_if_false_as_value_in_nested_dict(self):
        is_empty = is_empty_list_of_dicts([{"foo": {"en": False}}])
        self.assertFalse(is_empty)


class FindDictInListTest(TestCase):

    def setUp(self):
        self.l = [
            {
                "foo": "bar",
                "bar": "faz"
            }, {
                "foo": "faz"
            }, {
                "faz": "foo"
            }, {
                "foo": "bar"
            }
        ]

    def test_finds_dict(self):
        retu = find_dict_in_list(self.l, 'foo', 'faz')
        self.assertEqual(retu, {"foo": "faz"})

    def test_returns_not_found(self):
        retu = find_dict_in_list(self.l, 'foo', 'foo')
        self.assertEqual(retu, {})

    def test_returns_custom_not_found(self):
        retu = find_dict_in_list(self.l, 'foo', 'foo', not_found="foo")
        self.assertEqual(retu, "foo")

    def test_returns_first_occurence(self):
        retu = find_dict_in_list(self.l, 'foo', 'bar')
        self.assertEqual(retu, {"foo": "bar", "bar": "faz"})

    def test_returns_not_found_if_value_None(self):
        retu = find_dict_in_list(self.l, 'foo', None)
        self.assertEqual(retu, {})


class GetSessionQuestionnaireTest(TestCase):

    def setUp(self):
        self.request = Mock()
        self.request.session = {}

    def test_returns_empty_dict_if_no_session_questionnaire(self):
        ret = get_session_questionnaire(self.request, 'sample', 'code')
        self.assertEqual(ret, {})

    def test_returns_empty_dict_if_session_questionnaires_not_dict(self):
        self.request.session['questionnaires'] = 'foo'
        ret = get_session_questionnaire(self.request, 'sample', 'code')
        self.assertEqual(ret, {})

    def test_returns_empty_dict_if_session_questionnaire_empty(self):
        self.request.session['questionnaires'] = []
        ret = get_session_questionnaire(self.request, 'sample', 'code')
        self.assertEqual(ret, {})

    def test_returns_correct_session_questionnaire(self):
        self.request.session['questionnaires'] = [
            {
                'configuration_code': 'conf',
                'questionnaire_code': 'quest',
                'questionnaire': {'foo': 'bar'}
            },
            {
                'configuration_code': 'conf_foo',
                'questionnaire_code': 'quest_foo',
                'questionnaire': {'faz': 'taz'}
            }
        ]
        ret = get_session_questionnaire(self.request, 'conf', 'quest')
        self.assertEqual(
            ret, {
                'configuration_code': 'conf',
                'questionnaire_code': 'quest',
                'questionnaire': {'foo': 'bar'}
            })

    def test_returns_empty_if_not_found(self):
        self.request.session['questionnaires'] = [
            {
                'configuration_code': 'conf',
                'questionnaire_code': 'quest',
                'questionnaire': {'foo': 'bar'}
            },
            {
                'configuration_code': 'conf_foo',
                'questionnaire_code': 'quest_foo',
                'questionnaire': {'faz': 'taz'}
            }
        ]
        ret = get_session_questionnaire(self.request, 'foo', 'bar')
        self.assertEqual(ret, {})

    def test_returns_first_occurence_if_multiple_questionnaires(self):
        self.request.session['questionnaires'] = [
            {
                'configuration_code': 'conf',
                'questionnaire_code': 'quest',
                'questionnaire': {'foo': 'bar'}
            },
            {
                'configuration_code': 'conf',
                'questionnaire_code': 'quest',
                'questionnaire': {'faz': 'taz'}
            }
        ]
        ret = get_session_questionnaire(self.request, 'conf', 'quest')
        self.assertEqual(
            ret, {
                'configuration_code': 'conf',
                'questionnaire_code': 'quest',
                'questionnaire': {'foo': 'bar'}
            })


class SaveSessionQuestionnaireTest(TestCase):

    def setUp(self):
        self.request = Mock()
        self.request.session = {}

    def test_saves_questionnaire(self):
        self.assertIsNone(self.request.session.get('questionnaires'))
        save_session_questionnaire(
            self.request, 'sample', 'code', questionnaire_data={'data': 'bar'},
            questionnaire_links={'links': 'bar'})
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 1)
        q = q[0]
        self.assertEqual(len(q), 7)
        self.assertEqual(q['configuration_code'], 'sample')
        self.assertEqual(q['questionnaire_code'], 'code')
        self.assertEqual(q['questionnaire'], {'data': 'bar'})
        self.assertEqual(q['links'], {'links': 'bar'})
        self.assertIn('modified', q)

    def test_save_questionnaire_can_update_only_links(self):
        save_session_questionnaire(
            self.request, 'sample', 'code', questionnaire_data={'data': 'bar'},
            questionnaire_links={'links': 'bar'})
        save_session_questionnaire(
            self.request, 'sample', 'code',
            questionnaire_links={'links': 'foo'})
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 1)
        q = q[0]
        self.assertEqual(len(q), 7)
        self.assertEqual(q['configuration_code'], 'sample')
        self.assertEqual(q['questionnaire_code'], 'code')
        self.assertEqual(q['questionnaire'], {'data': 'bar'})
        self.assertEqual(q['links'], {'links': 'foo'})
        self.assertIn('modified', q)

    def test_save_questionnaire_saves_default_empty_dicts(self):
        save_session_questionnaire(self.request, 'sample', 'code')
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 1)
        q = q[0]
        self.assertEqual(len(q), 7)
        self.assertEqual(q['configuration_code'], 'sample')
        self.assertEqual(q['questionnaire_code'], 'code')
        self.assertEqual(q['questionnaire'], {})
        self.assertEqual(q['links'], {})
        self.assertIn('modified', q)

    def test_save_overwrites_existing_questionnaire(self):
        save_session_questionnaire(
            self.request, 'sample', 'code', {'data': 'foo'}, {'links': 'foo'})
        save_session_questionnaire(
            self.request, 'sample', 'code', {'data': 'bar'}, {'links': 'bar'})
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 1)
        q = q[0]
        self.assertEqual(len(q), 7)
        self.assertEqual(q['configuration_code'], 'sample')
        self.assertEqual(q['questionnaire_code'], 'code')
        self.assertEqual(q['questionnaire'], {'data': 'bar'})
        self.assertEqual(q['links'], {'links': 'bar'})
        self.assertIn('modified', q)


class ClearSessionQuestionnaireTest(TestCase):

    def setUp(self):
        self.request = Mock()
        self.request.session = {
            'questionnaires': [
                {
                    'configuration_code': 'conf',
                    'questionnaire_code': 'quest',
                    'questionnaire': {'foo': 'bar'}
                },
                {
                    'configuration_code': 'conf_foo',
                    'questionnaire_code': 'quest_foo',
                    'questionnaire': {'faz': 'taz'}
                }
            ]
        }

    def test_clears_questionnaire_if_found(self):
        clear_session_questionnaire(self.request, 'conf', 'quest')
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 1)
        q = q[0]
        self.assertEqual(q['configuration_code'], 'conf_foo')
        self.assertEqual(q['questionnaire_code'], 'quest_foo')
        self.assertEqual(q['questionnaire'], {'faz': 'taz'})

    def test_clears_nothing_if_not_found(self):
        clear_session_questionnaire(self.request, 'foo', 'bar')
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 2)

    def test_passes_if_session_empty(self):
        self.request.session = {
            'questionnaires': []
        }
        clear_session_questionnaire(self.request, 'foo', 'bar')
        q = self.request.session.get('questionnaires')
        self.assertIsInstance(q, list)
        self.assertEqual(len(q), 0)
