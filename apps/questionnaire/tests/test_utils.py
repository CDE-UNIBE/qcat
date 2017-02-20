# -*- coding: utf-8 -*-
import copy
from unittest.mock import patch, Mock, call, MagicMock

from collections import namedtuple

from django.conf import settings
from django.http import QueryDict
from django.test.utils import override_settings
from django.utils.translation import ugettext_lazy as _
from model_mommy import mommy

from accounts.models import User
from accounts.tests.test_models import create_new_user
from configuration.configuration import QuestionnaireConfiguration
from qcat.tests import TestCase
from questionnaire.errors import QuestionnaireLockedException
from questionnaire.models import Questionnaire, Flag, Lock
from questionnaire.serializers import QuestionnaireSerializer
from questionnaire.utils import (
    clean_questionnaire_data,
    compare_questionnaire_data,
    get_active_filters,
    get_questionnaire_data_in_single_language,
    get_questionnaire_data_for_translation_form,
    get_questiongroup_data_from_translation_form,
    get_link_data,
    get_link_display,
    get_list_values,
    handle_review_actions,
    is_valid_questionnaire_format,
    query_questionnaire,
    query_questionnaires,
    query_questionnaires_for_link,
    prepare_list_values)
from questionnaire.tests.test_models import get_valid_metadata, \
    get_valid_questionnaire
from qcat.errors import QuestionnaireFormatError


def get_valid_questionnaire_format():
    return {"foo": [{}]}


def get_valid_questionnaire_content():
    return {
        "qg_1": [{"key_1": {"en": "value_en", "es": "value_es"}}],
        "qg_3": [{"key_11": True}]
    }


class CleanQuestionnaireDataTest(TestCase):

    fixtures = ['sample_global_key_values.json', 'sample.json',
                'sample_projects.json']

    def setUp(self):
        self.conf = QuestionnaireConfiguration('sample')

    @patch('questionnaire.utils.is_valid_questionnaire_format')
    def test_calls_is_valid_questionnaire_format(
            self, mock_is_valid_questionnaire_format):
        data = get_valid_questionnaire_format()
        clean_questionnaire_data(data, QuestionnaireConfiguration('sample'))
        mock_is_valid_questionnaire_format.assert_called_once_with(data)

    def test_returns_error_list_if_invalid_questionnaire_format(self):
        data = 'foo'
        cleaned, errors = clean_questionnaire_data(data, None)
        self.assertEqual(len(errors), 1)

    def test_does_not_add_error_if_questiongroup_by_keyword_not_found(self):
        data = {
            "foo": [{"key_12": "1"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 0)

    def test_keeps_questiongroup_data_if_keyword_not_found(self):
        data = {
            "foo": [{"key_12": "1"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)

    def test_adds_error_if_key_not_valid_in_questiongroup(self):
        data = {
            "qg_9": [{"foo": "1"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_parses_measure_values_to_int(self):
        conf = QuestionnaireConfiguration('sample')
        data = {
            "qg_9": [{"key_12": "1"}]
        }
        cleaned, errors = clean_questionnaire_data(data, conf)
        self.assertEqual(cleaned, {"qg_9": [{"key_12": 1}]})
        self.assertEqual(len(errors), 0)

    def test_raises_error_if_measure_values_no_int(self):
        data = {
            "qg_9": [{"key_12": "foo"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_raises_error_if_measure_value_not_in_range(self):
        data = {
            "qg_9": [{"key_12": "0"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_clears_empty_questiongroups(self):
        data = get_valid_questionnaire_content()
        data['qg_9'] = []
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, get_valid_questionnaire_content())
        self.assertEqual(len(errors), 0)

    def test_clears_empty_questions(self):
        data = get_valid_questionnaire_content()
        data['qg_9'] = [{}]
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, get_valid_questionnaire_content())
        self.assertEqual(len(errors), 0)

    def test_clears_empty_values(self):
        data = get_valid_questionnaire_content()
        data['qg_9'] = [{"key_12": ""}]
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, get_valid_questionnaire_content())
        self.assertEqual(len(errors), 0)

    def test_string_values_need_to_be_dicts(self):
        data = {
            "qg_1": [{"key_1": "foo"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_list_values_need_to_be_lists(self):
        data = {
            "qg_10": [{"key_13": "value_13_1"}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_list_values_are_checked_correctly(self):
        data = {
            "qg_10": [{"key_13": ["value_13_1", "value_13_2"]}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_list_values_need_to_match_choices(self):
        data = {
            "qg_10": [{"key_13": ["value_13_1", "foo"]}]
        }
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_passes_if_conditional_question_correct(self):
        data = {
            "qg_12": [{"key_15": ["value_15_1"], "key_16": ["value_16_1"]}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    # def test_raises_error_if_conditional_question_not_correct(self):
    #     data = {
    #         "qg_12": [{"key_15": ["value_15_2"], "key_16": ["value_16_1"]}]}
    #     cleaned, errors = clean_questionnaire_data(data, self.conf)
    #     self.assertEqual(len(errors), 1)

    def test_passes_image_data_as_such(self):
        data = {"qg_14": [{"key_19": "61b51f3c-a3e2-43b7-87eb-42840bda7250"}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 0)
        self.assertEqual(cleaned, data)

    def test_passes_if_conditional_questiongroup_correct(self):
        data = {'qg_17': [{'key_23': {'en': 'Bar'}}], 'qg_16': [{'key_21': 2}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_raises_error_if_conditional_questiongroup_not_correct(self):
        data = {'qg_17': [{'key_23': {'en': 'Bar'}}], 'qg_16': [{'key_21': 1}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_passes_if_conditional_questiongroup_without_data(self):
        data = {'qg_17': [{'key_23': {'en': ''}, 'key_22': []}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, {})
        self.assertEqual(len(errors), 0)

    def test_passes_with_conditional_checkbox_questiongroup(self):
        data = {
            'qg_10': [{'key_13': ['value_13_5']}],
            'qg_18': [{'key_24': {'en': 'Bar'}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_passes_with_conditional_multiple_checkbox_questiongroup(self):
        data = {
            'qg_10': [{'key_13': ['value_13_5', 'value_13_4']}],
            'qg_18': [{'key_24': {'en': 'Bar'}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_fails_with_conditional_checkbox_questiongroup(self):
        data = {
            'qg_10': [{'key_13': ['value_13_4']}],
            'qg_18': [{'key_24': {'en': 'Bar'}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_fails_if_text_length_exceeds_max_length(self):
        data = {'qg_2': [{
            'key_2':
            {'en': 'The limit is 50 chars but this text contains 55 chars.'},
            'key_3': {'en': ''}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_passes_if_text_length_below_max_length(self):
        data = {'qg_2': [{'key_2': {'en': 'This is short enough.'}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_passes_with_boolean_True_as_integer(self):
        data = {'qg_3': [{'key_11': 1}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_passes_with_boolean_False_as_integer(self):
        data = {'qg_3': [{'key_11': 0}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_fails_with_boolean_impossible_value_as_integer(self):
        data = {'qg_3': [{'key_11': 99}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_passes_if_num_lower_than_max_num_of_questiongroups(self):
        data = {'qg_6': [
            {'key_8': {'en': 'Key 8 - 1'}},
            {'key_8': {'en': 'Key 8 - 2'}},
            {'key_8': {'en': 'Key 8 - 3'}}
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(cleaned, data)
        self.assertEqual(len(errors), 0)

    def test_raises_error_if_num_higher_than_max_num_of_questiongroups(self):
        data = {'qg_6': [
            {'key_8': {'en': 'Key 8 - 1'}},
            {'key_8': {'en': 'Key 8 - 2'}},
            {'key_8': {'en': 'Key 8 - 3'}},
            {'key_8': {'en': 'Key 8 - 4'}}
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_orders_questiongroups(self):
        data = {'qg_7': [
            {'key_9': {'en': 'Key 9 - 1'}, '__order': 2},
            {'key_9': {'en': 'Key 9 - 2'}, '__order': 1},
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 0)
        self.assertEqual(cleaned['qg_7'][0]['key_9']['en'], 'Key 9 - 2')
        self.assertEqual(cleaned['qg_7'][1]['key_9']['en'], 'Key 9 - 1')

    def test_questiongroups_can_be_unordered(self):
        data = {'qg_7': [
            {'key_9': {'en': 'Key 9 - 1'}},
            {'key_9': {'en': 'Key 9 - 2'}},
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 0)

    def test_questiongroup_is_removed_if_only_order(self):
        data = {'qg_7': [
            {'__order': 1},
            {'__order': 2},
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 0)
        self.assertEqual(cleaned, {})

    def test_select_model_checks_valid_model(self):
        data = {"qg_37": [
            {"key_52": "4", "key_53": "Non-existing project"}
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(len(errors), 1)

    def test_select_model_parses_to_int(self):
        data = {"qg_37": [
            {"key_52": "2", "key_53": "Some project"}
        ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(errors, [])
        self.assertEqual(cleaned['qg_37'][0]['key_52'], 2)

    def test_select_conditional_questiongroup_cleaned_if_qg_not_available(self):
        # No qg_41
        data = {
            "qg_44": [{"key_60": "qg_41", "key_61": {"en": "foo"}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(errors, [])
        self.assertEqual(cleaned['qg_44'], [{"key_61": {"en": "foo"}}])

    def test_select_conditional_questiongroup_cleaned_if_qg_not_available_2(self):
        # No qg_41
        data = {
            "qg_41": [{"key_57": ""}],
            "qg_44": [{"key_60": "qg_41", "key_61": {"en": "foo"}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(errors, [])
        self.assertEqual(cleaned['qg_44'], [{"key_61": {"en": "foo"}}])

    def test_select_conditional_questiongroup_cleaned_if_qg_not_available_multi(
            self):
        # No qg_41
        data = {
            "qg_42": [{"key_57": "value_57_3"}],
            "qg_44": [
                {"key_60": "qg_41", "key_61": {"en": "foo"}},
                {"key_60": "qg_42", "key_61": {"en": "bar"}}
            ]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(errors, [])
        self.assertEqual(len(cleaned['qg_44']), 2)
        self.assertIn({"key_61": {"en": "foo"}}, cleaned['qg_44'])
        self.assertIn(
            {"key_60": "qg_42", "key_61": {"en": "bar"}}, cleaned['qg_44'])

    def test_select_conditional_questiongroup_passes(self):
        # qg_41 available
        data = {
            "qg_41": [{"key_57": "value_57_3"}],
            "qg_44": [{"key_60": "qg_41", "key_61": {"en": "foo"}}]}
        cleaned, errors = clean_questionnaire_data(data, self.conf)
        self.assertEqual(errors, [])
        self.assertEqual(cleaned, data)


class IsValidQuestionnaireFormatTest(TestCase):

    def test_raises_error_if_invalid_format(self):
        with self.assertRaises(QuestionnaireFormatError):
            is_valid_questionnaire_format("foo")

    def test_raises_error_if_invalid_format2(self):
        with self.assertRaises(QuestionnaireFormatError):
            is_valid_questionnaire_format({"foo": "bar"})

    def test_returns_true_if_valid_format(self):
        self.assertTrue(is_valid_questionnaire_format(
            get_valid_questionnaire_format()))


class GetQuestionnaireDataInSingleLanguageTest(TestCase):

    @patch('questionnaire.utils.is_valid_questionnaire_format')
    def test_calls_is_valid_questionnaire_format(
            self, mock_is_valid_questionnaire_format):
        data = get_valid_questionnaire_format()
        get_questionnaire_data_in_single_language(data, locale='en')
        mock_is_valid_questionnaire_format.assert_called_once_with(data)

    def test_returns_single_value_per_key(self):
        data = get_valid_questionnaire_content()
        data_es = get_questionnaire_data_in_single_language(data, locale='es')
        self.assertEqual(len(data), len(data_es))
        self.assertEqual(len(data['qg_1']), len(data_es['qg_1']))
        self.assertEqual(data_es['qg_1'][0]['key_1'], 'value_es')

    def test_sets_None_if_locale_not_found(self):
        data = get_valid_questionnaire_content()
        data_foo = get_questionnaire_data_in_single_language(
            data, locale='foo')
        self.assertIsNone(data_foo['qg_1'][0]['key_1'])

    def test_also_returns_non_translated_values(self):
        data = get_valid_questionnaire_content()
        data_es = get_questionnaire_data_in_single_language(data, locale='es')
        self.assertEqual(data_es['qg_3'][0]['key_11'], True)


class GetQuestionnaireDataForTranslationFormTest(TestCase):

    @patch('questionnaire.utils.is_valid_questionnaire_format')
    def test_calls_is_valid_questionnaire_format(
            self, mock_is_valid_questionnaire_format):
        data = get_valid_questionnaire_format()
        get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale='en')
        mock_is_valid_questionnaire_format.assert_called_once_with(data)

    def test_adds_translation_fields(self):
        data = get_valid_questionnaire_content()
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale='en')
        self.assertEqual(len(data), len(data_trans))
        self.assertEqual(len(data['qg_1']), len(data_trans['qg_1']))
        self.assertEqual(
            data_trans['qg_1'][0]['old_key_1'], data['qg_1'][0]['key_1'])
        self.assertEqual(
            data_trans['qg_1'][0]['original_key_1'],
            data['qg_1'][0]['key_1']['en'])
        self.assertEqual(
            data_trans['qg_1'][0]['translation_key_1'],
            data['qg_1'][0]['key_1']['es'])

    def test_uses_current_locale_if_original_is_None(self):
        data = get_valid_questionnaire_content()
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale=None)
        self.assertEqual(
            data_trans['qg_1'][0]['original_key_1'],
            data['qg_1'][0]['key_1']['es'])
        self.assertEqual(
            data_trans['qg_1'][0]['translation_key_1'],
            data['qg_1'][0]['key_1']['es'])

    def test_also_returns_non_translated_values(self):
        data = get_valid_questionnaire_content()
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale='en')
        self.assertEqual(data_trans['qg_3'][0]['key_11'], True)


class GetQuestiongroupDataFromTranslationFormTest(TestCase):

    def test_uses_current_locale_if_original_is_None(self):
        data = get_valid_questionnaire_content()
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale=None)
        qg_1_cleaned = get_questiongroup_data_from_translation_form(
            data_trans['qg_1'][0], 'es', None)
        self.assertEqual(qg_1_cleaned, data['qg_1'][0])

    def test_cleans_translation_fields(self):
        data = get_valid_questionnaire_content()
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale='en')
        qg_1_cleaned = get_questiongroup_data_from_translation_form(
            data_trans['qg_1'][0], 'es', 'en')
        self.assertEqual(qg_1_cleaned, data['qg_1'][0])

    def test_handles_keys_with_keyword_in_them(self):
        data = {
            "qg_1": [{"wocat_original_landuse": {
                "en": "value_en", "es": "value_es"}}],
        }
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale='en')
        qg_1_cleaned = get_questiongroup_data_from_translation_form(
            data_trans['qg_1'][0], 'es', 'en')
        self.assertEqual(qg_1_cleaned, data['qg_1'][0])

    def test_returns_non_translated_values(self):
        data = get_valid_questionnaire_content()
        data_trans = get_questionnaire_data_for_translation_form(
            data, current_locale='es', original_locale='en')
        qg_3_cleaned = get_questiongroup_data_from_translation_form(
            data_trans['qg_3'][0], 'es', 'en')
        self.assertEqual(qg_3_cleaned, data['qg_3'][0])


class GetActiveFiltersTest(TestCase):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def setUp(self):
        self.conf = QuestionnaireConfiguration('sample')

    def test_returns_empty_if_empty_query_dict(self):
        query_dict = QueryDict('')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(filters, [])

    def test_returns_empty_if_no_filter(self):
        query_dict = QueryDict('a=1&b=2')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(filters, [])

    def test_skips_invalid_filters(self):
        query_dict = QueryDict('filter__foo=1&filter__foo__bar__faz=2')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(filters, [])

    def test_skips_filter_with_unknown_questiongroup_or_key(self):
        query_dict = QueryDict(
            'filter__qg_1__unknown_key=1&filter__inv_qg__key_1=2')
        filters = get_active_filters([self.conf], query_dict)
        self.assertEqual(filters, [])

    def test_returns_single_query_dict(self):
        query_dict = QueryDict(
            'filter__qg_11__key_14=value_14_1')
        filters = get_active_filters([self.conf], query_dict)
        self.assertEqual(len(filters), 1)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['questiongroup'], 'qg_11')
        self.assertEqual(filter_1['key'], 'key_14')
        self.assertEqual(filter_1['key_label'], 'Key 14')
        self.assertEqual(filter_1['value'], 'value_14_1')
        self.assertEqual(filter_1['value_label'], 'Value 14_1')
        self.assertEqual(filter_1['type'], 'image_checkbox')

    def test_returns_multiple_filters(self):
        query_dict = QueryDict(
            'filter__qg_11__key_14=value_14_1&filter__qg_19__key_5=Faz')
        filters = get_active_filters([self.conf], query_dict)
        self.assertEqual(len(filters), 2)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['key_label'], 'Key 14')
        self.assertEqual(filter_1['value_label'], 'Value 14_1')
        filter_2 = filters[1]
        self.assertIsInstance(filter_2, dict)
        self.assertEqual(len(filter_2), 6)
        self.assertEqual(filter_2['key_label'], 'Key 5')
        self.assertEqual(filter_2['value_label'], 'Faz')

    def test_returns_duplicate_filter_keys(self):
        query_dict = QueryDict(
            'filter__qg_11__key_14=value_14_1&filter__qg_11__key_14='
            'value_14_2')
        filters = get_active_filters([self.conf], query_dict)
        self.assertEqual(len(filters), 2)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['key_label'], 'Key 14')
        self.assertEqual(filter_1['value_label'], 'Value 14_1')
        filter_2 = filters[1]
        self.assertIsInstance(filter_2, dict)
        self.assertEqual(len(filter_2), 6)
        self.assertEqual(filter_2['key_label'], 'Key 14')
        self.assertEqual(filter_2['value_label'], 'Value 14_2')

    def test_returns_q_filter(self):
        query_dict = QueryDict('q=foo')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(len(filters), 1)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['type'], '_search')
        self.assertEqual(filter_1['key'], '_search')
        self.assertEqual(filter_1['questiongroup'], '_search')
        self.assertEqual(filter_1['key_label'], 'Search Terms')
        self.assertEqual(filter_1['value'], 'foo')
        self.assertEqual(filter_1['value_label'], 'foo')

    def test_returns_created_filter(self):
        query_dict = QueryDict('created=2014-2016')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(len(filters), 1)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['type'], '_date')
        self.assertEqual(filter_1['key'], 'created')
        self.assertEqual(filter_1['questiongroup'], 'created')
        self.assertEqual(filter_1['key_label'], 'Created')
        self.assertEqual(filter_1['value'], '2014-2016')
        self.assertEqual(filter_1['value_label'], '2014 - 2016')

    def test_handles_invalid_created_dates(self):
        query_dict = QueryDict('created=2014')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(len(filters), 0)

    def test_handles_invalid_updated_dates(self):
        query_dict = QueryDict('updated=foo-bar')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(len(filters), 0)

    def test_returns_flag_filter(self):
        Flag.objects.create(flag='unccd_bp')
        query_dict = QueryDict('flag=unccd_bp')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(len(filters), 1)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['type'], '_flag')
        self.assertEqual(filter_1['key'], 'flag')
        self.assertEqual(filter_1['questiongroup'], 'flag')
        self.assertEqual(filter_1['key_label'], '')
        self.assertEqual(filter_1['value'], 'unccd_bp')
        self.assertEqual(filter_1['value_label'], 'UNCCD Best Practice')

    def test_returns_unknown_flag_filter(self):
        query_dict = QueryDict('flag=unknown')
        filters = get_active_filters(self.conf, query_dict)
        self.assertEqual(len(filters), 1)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['type'], '_flag')
        self.assertEqual(filter_1['key'], 'flag')
        self.assertEqual(filter_1['questiongroup'], 'flag')
        self.assertEqual(filter_1['key_label'], '')
        self.assertEqual(filter_1['value'], 'unknown')
        self.assertEqual(filter_1['value_label'], 'Unknown')

    def test_returns_mixed_filters(self):
        query_dict = QueryDict('q=foo&filter__qg_11__key_14=value_14_1')
        filters = get_active_filters([self.conf], query_dict)
        self.assertEqual(len(filters), 2)
        filter_1 = filters[0]
        self.assertIsInstance(filter_1, dict)
        self.assertEqual(len(filter_1), 6)
        self.assertEqual(filter_1['type'], '_search')
        self.assertEqual(filter_1['key'], '_search')
        self.assertEqual(filter_1['questiongroup'], '_search')
        self.assertEqual(filter_1['key_label'], 'Search Terms')
        self.assertEqual(filter_1['value'], 'foo')
        self.assertEqual(filter_1['value_label'], 'foo')
        filter_2 = filters[1]
        self.assertIsInstance(filter_2, dict)
        self.assertEqual(len(filter_2), 6)
        self.assertEqual(filter_2['key_label'], 'Key 14')
        self.assertEqual(filter_2['value_label'], 'Value 14_1')


class GetLinkDataTest(TestCase):

    @patch('questionnaire.utils.ConfigurationList')
    def test_creates_configuration_list(self, mock_ConfigurationList):
        get_link_data([])
        mock_ConfigurationList.assert_called_once_with()

    @patch('questionnaire.utils.get_link_display')
    def test_uses_first_code_if_none_provided(self, mock_get_link_display):
        link = Mock()
        link.configurations.first.return_value.code = 'foo'
        link_data = get_link_data([link])
        self.assertIn('foo', link_data)

    @patch('questionnaire.utils.get_link_display')
    def test_uses_code_provided(self, mock_get_link_display):
        link = Mock()
        link.configurations.first.return_value.code = 'faz'
        link_data = get_link_data([link], link_configuration_code='foo')
        self.assertIn('foo', link_data)

    @patch('questionnaire.utils.get_link_display')
    def test_calls_get_link_display(self, mock_get_link_display):
        link = Mock()
        link.configurations.first.return_value.code = 'foo'
        get_link_data([link])
        mock_get_link_display.assert_called_once_with(
            'foo', 'Unknown name', link.code)

    @patch('questionnaire.utils.get_link_display')
    def test_return_values(self, mock_get_link_display):
        link = Mock()
        link.configurations.first.return_value.code = 'foo'
        link_data = get_link_data([link])
        self.assertEqual(link_data, {'foo': [{
            'code': link.code,
            'configuration': link.get_original_configuration().code,
            'id': link.id,
            'link': mock_get_link_display.return_value,
            'name': 'Unknown name',
        }]})


class GetLinkDisplayTest(TestCase):

    @patch('questionnaire.utils.render_to_string')
    def test_calls_render_to_string(self, mock_render_to_string):
        get_link_display('configuration', 'name', 'identifier')
        mock_render_to_string.assert_called_once_with(
            'configuration/questionnaire/partial/link.html', {
                'name': 'name',
                'link_route': 'configuration:questionnaire_details',
                'questionnaire_identifier': 'identifier',
            })

    @patch('questionnaire.utils.render_to_string')
    def test_returns_render_to_string(self, mock_render_to_string):
        link_display = get_link_display('configuration', 'name', 'identifier')
        self.assertEqual(link_display, mock_render_to_string.return_value)


class QueryQuestionnaireTest(TestCase):

    @patch('questionnaire.utils.get_query_status_filter')
    @patch('questionnaire.utils.Questionnaire')
    def test_calls_status_filter(
            self, mock_Questionnaire, mock_get_query_status_filter):
        request = Mock()
        query_questionnaire(request, 'sample')
        mock_get_query_status_filter.assert_called_once_with(request)


class GetQueryStatusFilter(TestCase):

    # This is tested implicitely through QueryQuestionnairesTest
    pass


class QueryQuestionnairesTest(TestCase):

    fixtures = [
        'groups_permissions.json', 'sample.json',
        'sample_questionnaire_status.json']

    @patch('questionnaire.utils.get_query_status_filter')
    @patch('questionnaire.utils.Questionnaire')
    def test_calls_status_filter(
            self, mock_Questionnaire, mock_get_query_status_filter):
        request = Mock()
        query_questionnaires(request, 'sample')
        mock_get_query_status_filter.assert_called_once_with(request)

    def test_public_only_returns_public(self):
        request = Mock()
        request.user.is_authenticated.return_value = False
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0].id, 3)
        self.assertEqual(ret[1].id, 6)

    def test_user_sees_his_own_draft_submitted_reviewed_user_101(self):
        request = Mock()
        request.user = User.objects.get(pk=101)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 6)
        self.assertEqual(ret[0].id, 1)
        self.assertEqual(ret[1].id, 3)
        self.assertEqual(ret[2].id, 6)
        self.assertEqual(ret[3].id, 8)
        self.assertEqual(ret[4].id, 9)
        self.assertEqual(ret[5].id, 10)

    def test_user_sees_his_own_draft_submitted_reviewed_user_102(self):
        request = Mock()
        request.user = User.objects.get(pk=102)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 4)
        self.assertEqual(ret[0].id, 2)
        self.assertEqual(ret[1].id, 3)
        self.assertEqual(ret[2].id, 6)
        self.assertEqual(ret[3].id, 9)

    def test_reviewer_sees_submitted_and_own_drafts_103(self):
        # User 103 is reviewer, he sees all submitted
        request = Mock()
        request.user = User.objects.get(pk=103)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 5)
        self.assertEqual(ret[0].id, 2)
        self.assertEqual(ret[1].id, 3)
        self.assertEqual(ret[2].id, 6)
        self.assertEqual(ret[3].id, 7)
        self.assertEqual(ret[4].id, 9)

    def test_reviewer_sees_submitted_and_own_drafts_102(self):
        # User 102 is only reviewer for 9
        request = Mock()
        request.user = User.objects.get(pk=102)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 4)
        self.assertEqual(ret[0].id, 2)
        self.assertEqual(ret[1].id, 3)
        self.assertEqual(ret[2].id, 6)
        self.assertEqual(ret[3].id, 9)

    def test_publisher_sees_reviewed_and_own_drafts_104(self):
        # User 104 is publisher, sees all reviewed
        request = Mock()
        request.user = User.objects.get(pk=104)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 4)
        self.assertEqual(ret[0].id, 3)
        self.assertEqual(ret[1].id, 6)
        self.assertEqual(ret[2].id, 8)
        self.assertEqual(ret[3].id, 10)

    def test_publisher_sees_reviewed_and_own_drafts_106(self):
        request = Mock()
        request.user = User.objects.get(pk=106)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 3)
        self.assertEqual(ret[0].id, 3)
        self.assertEqual(ret[1].id, 6)
        self.assertEqual(ret[2].id, 10)

    def test_reviewer_publishes_sees_almost_everything(self):
        request = Mock()
        request.user = User.objects.get(pk=105)
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 6)
        self.assertEqual(ret[0].id, 2)
        self.assertEqual(ret[1].id, 3)
        self.assertEqual(ret[2].id, 6)
        self.assertEqual(ret[3].id, 8)
        self.assertEqual(ret[4].id, 9)
        self.assertEqual(ret[5].id, 10)

    def test_only_one_version_is_visible(self):
        user = User.objects.get(pk=101)
        prev_version = Questionnaire.objects.get(pk=3)
        Questionnaire.create_new(
            'sample', {}, user, previous_version=prev_version, status=3)
        request = Mock()
        request.user = user
        ret = query_questionnaires(request, 'sample')
        self.assertEqual(len(ret), 6)
        self.assertEqual(ret[0].id, 11)
        self.assertEqual(ret[1].id, 1)
        self.assertEqual(ret[2].id, 6)
        self.assertEqual(ret[3].id, 8)
        self.assertEqual(ret[4].id, 9)
        self.assertEqual(ret[5].id, 10)

    def test_own_reviewer_sees_only_one_version(self):
        # A user who is the reviewer of his own questionnaire should only see
        # one version of it
        user = User.objects.get(pk=103)
        questionnaire = Questionnaire.objects.get(pk=7)
        questionnaire.add_user(user, 'reviewer')
        request = Mock()
        request.user = user
        ret = query_questionnaires(
            request, 'all', only_current=False, limit=None, user=user)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].id, 7)

    def test_applies_limit(self):
        request = Mock()
        request.user.is_authenticated.return_value = False
        ret = query_questionnaires(request, 'sample', limit=1)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].id, 3)

    def test_applies_offset(self):
        request = Mock()
        request.user.is_authenticated.return_value = False
        ret = query_questionnaires(request, 'sample', offset=1)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].id, 6)


class QueryQuestionnairesForLinkTest(TestCase):

    fixtures = [
        'sample_global_key_values.json', 'sample.json',
        'sample_questionnaires.json']

    def setUp(self):
        req = Mock()
        req.user.is_authenticated.return_value = False
        self.request = req

    def test_calls_get_name_keywords(self):
        configuration = Mock()
        configuration.get_name_keywords.return_value = None, None
        query_questionnaires_for_link(self.request, configuration, '')
        configuration.get_name_keywords.assert_called_once_with()

    def test_returns_empty_if_no_name(self):
        configuration = Mock()
        configuration.get_name_keywords.return_value = None, None
        total, data = query_questionnaires_for_link(
            self.request, configuration, '')
        self.assertEqual(total, 0)
        self.assertEqual(data, [])

    def test_returns_by_q(self):
        configuration = QuestionnaireConfiguration('sample')
        q = 'key'
        total, data = query_questionnaires_for_link(
            self.request, configuration, q)
        self.assertEqual(total, 2)
        self.assertTrue(len(data), 2)
        self.assertEqual(data[0].id, 1)
        self.assertEqual(data[1].id, 2)

    def test_returns_by_q_case_insensitive(self):
        configuration = QuestionnaireConfiguration('sample')
        q = 'KEY'
        total, data = query_questionnaires_for_link(
            self.request, configuration, q)
        self.assertEqual(total, 2)
        self.assertTrue(len(data), 2)
        self.assertEqual(data[0].id, 1)
        self.assertEqual(data[1].id, 2)

    def test_returns_single_result(self):
        configuration = QuestionnaireConfiguration('sample')
        q = 'key 1b'
        total, data = query_questionnaires_for_link(
            self.request, configuration, q)
        self.assertEqual(total, 1)
        self.assertTrue(len(data), 1)
        self.assertEqual(data[0].id, 2)

    def test_applies_limit(self):
        configuration = QuestionnaireConfiguration('sample')
        q = 'key'
        total, data = query_questionnaires_for_link(
            self.request, configuration, q, limit=1)
        self.assertEqual(total, 2)
        self.assertTrue(len(data), 1)
        self.assertEqual(data[0].id, 1)

    def test_finds_by_code(self):
        configuration = QuestionnaireConfiguration('sample')
        q = 'sample_1'
        total, data = query_questionnaires_for_link(
            self.request, configuration, q)
        self.assertEqual(total, 1)
        self.assertTrue(len(data), 1)
        self.assertEqual(data[0].id, 1)

    def test_find_by_other_langauge(self):
        configuration = QuestionnaireConfiguration('sample')
        q = 'clave'
        total, data = query_questionnaires_for_link(
            self.request, configuration, q)
        self.assertEqual(total, 1)
        self.assertTrue(len(data), 1)
        self.assertEqual(data[0].id, 2)


@override_settings(USE_CACHING=False)
class GetListValuesTest(TestCase):

    fixtures = ['sample_global_key_values.json', 'sample.json']

    def setUp(self):
        self.values_length = 13
        self.es_hits = [{'_id': 1}]

    def test_serializer_uses_provided_configuration(self):
        # get_valid_questionnaire uses the config 'sample' by default.
        serialized = QuestionnaireSerializer(
            get_valid_questionnaire(),
            config=QuestionnaireConfiguration('sample_core')
        )
        ret = get_list_values(
            es_hits=[{'_source': serialized.data}],
            configuration_code='sample_core'
        )
        self.assertEqual(len(ret), 1)
        ret_1 = ret[0]

        self.assertEqual(ret_1.get('configuration'), 'sample_core')

    def test_es_wocat_uses_default_configuration(self):
        serialized = QuestionnaireSerializer(
            get_valid_questionnaire()
        )
        ret = get_list_values(
            es_hits=[{'_source': serialized.data}], configuration_code='wocat'
        )
        self.assertEqual(len(ret), 1)
        ret_1 = ret[0]
        self.assertEqual(ret_1.get('configuration'), 'sample')

    @patch('questionnaire.utils.get_link_data')
    def test_returns_values_from_database(self, mock_get_link_data):
        obj = Mock()
        obj.configurations.all.return_value = []
        obj.configurations.first.return_value = None
        obj.links.all.return_value = []
        obj.questionnairetranslation_set.all.return_value = []
        obj.get_metadata.return_value = get_valid_metadata()
        questionnaires = [obj]
        ret = get_list_values(questionnaire_objects=questionnaires)
        self.assertEqual(len(ret), 1)
        ret_1 = ret[0]
        self.assertEqual(len(ret_1), self.values_length)
        self.assertEqual(ret_1.get('configuration'), 'technologies')
        self.assertEqual(ret_1.get('configurations'), ['configuration'])
        self.assertEqual(ret_1.get('created', ''), 'created')
        self.assertEqual(ret_1.get('updated', ''), 'updated')
        self.assertEqual(ret_1.get('native_configuration'), False)
        self.assertEqual(ret_1.get('id'), obj.id)
        self.assertEqual(ret_1.get('translations'), [])
        self.assertEqual(ret_1.get('code'), 'code')
        self.assertEqual(ret_1.get('compilers'), ['compiler'])
        self.assertEqual(ret_1.get('editors'), ['editor'])
        self.assertEqual(ret_1.get('links'), {})

    @patch('questionnaire.utils.get_link_data')
    def test_db_uses_provided_configuration(self, mock_get_link_data):
        obj = Mock()
        obj.configurations.all.return_value = []
        obj.configurations.first.return_value = None
        obj.links.all.return_value = []
        obj.questionnairetranslation_set.all.return_value = []
        obj.get_metadata.return_value = get_valid_metadata()
        questionnaires = [obj]
        ret = get_list_values(
            questionnaire_objects=questionnaires, configuration_code='foo')
        self.assertEqual(len(ret), 1)
        ret_1 = ret[0]
        self.assertEqual(len(ret_1), self.values_length)
        self.assertEqual(ret_1.get('configuration'), 'foo')

    @patch('questionnaire.utils.get_link_data')
    def test_db_wocat_uses_default_configuration(self, mock_get_link_data):
        obj = Mock()
        obj.configurations.all.return_value = []
        obj.configurations.first.return_value = None
        obj.links.all.return_value = []
        obj.questionnairetranslation_set.all.return_value = []
        obj.get_metadata.return_value = get_valid_metadata()
        questionnaires = [obj]
        ret = get_list_values(
            questionnaire_objects=questionnaires, configuration_code='wocat')
        self.assertEqual(len(ret), 1)
        ret_1 = ret[0]
        self.assertEqual(len(ret_1), self.values_length)
        self.assertEqual(ret_1.get('configuration'), 'technologies')

    @patch.object(QuestionnaireSerializer, 'to_list_values')
    def test_to_value_calls_prepare_data(self, mock_to_list_values):
        obj = get_valid_questionnaire()
        serialized = QuestionnaireSerializer(obj).data
        get_list_values(es_hits=[{'_source': serialized}])
        mock_to_list_values.assert_called_with(lang='en')

    def test_prepare_list_values(self):
        obj = get_valid_questionnaire()
        serializer = QuestionnaireSerializer(obj).data
        object_data = get_list_values(
            questionnaire_objects=[obj], with_links=False
        )[0]
        serializer_data = get_list_values(
            es_hits=[{'_source': serializer}]
        )[0]
        keys = ['url', 'compilers', 'data']
        for key in keys:
            self.assertEqual(serializer_data[key], object_data[key])

    def test_prepare_list_values_with_i18n(self):
        data = {
            'list_data': {
                'name': {'en': 'foo'},
                'country': _(u'Login')
            },
            'translations': ['en'],
            'configurations': ['sample']
        }
        configuration = MagicMock()
        configuration.keyword = 'foo'
        prepared = prepare_list_values(data, configuration)
        self.assertEqual(prepared['country'], _(u'Login'))
        self.assertEqual(prepared['name'], 'foo')


@patch('questionnaire.utils.messages')
class HandleReviewActionsTest(TestCase):

    def setUp(self):
        self.request = Mock()
        self.request.user = Mock()
        self.obj = Mock(spec=Questionnaire)
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=[])
        self.obj.links.all.return_value = []

    def test_submit_error_if_previous_status_wrong(self, mock_messages):
        self.obj.status = 3
        self.request.POST = {'submit': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 3)
        mock_messages.error.assert_called_once_with(
            self.request,
            'The questionnaire could not be submitted because it does not have'
            ' to correct status.')

    def test_submit_needs_permissions(self, mock_messages):
        self.obj.status = 1
        self.request.POST = {'submit': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 1)
        mock_messages.error.assert_called_once_with(
            self.request,
            'The questionnaire could not be submitted because you do not have '
            'permission to do so.')

    @patch('questionnaire.signals.change_status.send')
    def test_submit_updates_status(self, moc_change_status, mock_messages):
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['submit_questionnaire'])
        self.obj.status = 1
        self.request.POST = {'submit': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 2)
        mock_messages.success.assert_called_once_with(
            self.request,
            'The questionnaire was successfully submitted.')

    def test_submit_fails_for_locked_questionnaire(self, mock_messages):
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])

        questionnaire = mommy.make(
            Questionnaire,
            code='007',
            status=1
        )
        questionnaire.get_roles_permissions = lambda user: RolesPermissions(
            roles=[], permissions=['submit_questionnaire'])
        mommy.make(
            Lock,
            questionnaire_code=questionnaire.code,
            user=create_new_user(),
            is_finished=False
        )
        self.request.POST = {'submit': 'foo'}
        self.request.user = create_new_user(id=2, email='oddjob@mean.com')
        with self.assertRaises(QuestionnaireLockedException):
            handle_review_actions(self.request, questionnaire, 'sample')

    def test_submit_succeeds_for_locked_compiler(self, mock_messages):
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])

        questionnaire = mommy.make(
            Questionnaire,
            code='007',
            status=1
        )
        questionnaire.get_roles_permissions = lambda user: RolesPermissions(
            roles=[], permissions=['submit_questionnaire'])

        compiler = create_new_user()

        mommy.make(
            Lock,
            questionnaire_code=questionnaire.code,
            user=compiler,
            is_finished=False
        )
        self.request.POST = {'submit': 'foo'}
        self.request.user = compiler
        handle_review_actions(self.request, questionnaire, 'sample')
        self.assertEqual(
            questionnaire.status, settings.QUESTIONNAIRE_SUBMITTED
        )

    def test_review_error_if_previous_status_wrong(self, mock_messages):
        self.obj.status = 3
        self.request.POST = {'review': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 3)
        mock_messages.error.assert_called_once_with(
            self.request,
            'The questionnaire could not be reviewed because it does not have '
            'to correct status.')

    def test_review_needs_permissions(self, mock_messages):
        self.obj.status = 2
        self.request.POST = {'review': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 2)
        mock_messages.error.assert_called_once_with(
            self.request,
            'The questionnaire could not be reviewed because you do not have '
            'permission to do so.')

    @patch('questionnaire.signals.change_status.send')
    def test_review_updates_status(self, mock_change_status, mock_messages):
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['review_questionnaire'])
        self.obj.status = 2
        self.request.POST = {'review': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 3)
        mock_messages.success.assert_called_once_with(
            self.request,
            'The questionnaire was successfully reviewed.')

    def test_publish_error_if_previous_status_wrong(self, mock_messages):
        self.obj.status = 1
        self.request.POST = {'publish': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 1)
        mock_messages.error.assert_called_once_with(
            self.request,
            'The questionnaire could not be published because it does not '
            'have to correct status.')

    def test_publish_needs_permissions(self, mock_messages):
        self.obj.status = 3
        self.request.POST = {'publish': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 3)
        mock_messages.error.assert_called_once_with(
            self.request,
            'The questionnaire could not be published because you do not have '
            'permission to do so.')

    @patch('questionnaire.utils.Questionnaire')
    @patch('questionnaire.utils.delete_questionnaires_from_es')
    @patch('questionnaire.utils.put_questionnaire_data')
    @patch('questionnaire.signals.change_status.send')
    def test_publish_updates_status_of_previously_public(
            self, mock_change_status, mock_put_data, mock_delete_data,
            mock_Questionnaire, mock_messages):
        mock_put_data.return_value = None, []
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['publish_questionnaire'])
        self.obj.status = 3
        self.obj.code = 'code'
        self.obj.links.filter.return_value = []
        self.request.user = Mock()
        self.request.POST = {'publish': 'foo'}
        prev = Mock()
        mock_Questionnaire.objects.filter.return_value = [prev]
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(prev.status, 6)
        prev.save.assert_called_once_with()

    @patch('questionnaire.utils.Questionnaire')
    @patch('questionnaire.utils.delete_questionnaires_from_es')
    @patch('questionnaire.utils.put_questionnaire_data')
    @patch('questionnaire.signals.change_status.send')
    def test_publish_removes_previously_public_from_es(
            self, mock_change_status, mock_put_data, mock_delete_data,
            mock_Questionnaire, mock_messages):
        mock_put_data.return_value = None, []
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['publish_questionnaire'])
        self.obj.status = 3
        self.obj.code = 'code'
        self.obj.links.filter.return_value = []
        self.request.user = Mock()
        self.request.POST = {'publish': 'foo'}
        prev = Mock()
        mock_Questionnaire.objects.filter.return_value = [prev]
        handle_review_actions(self.request, self.obj, 'sample')
        mock_delete_data.assert_called_once_with('sample', [prev])

    @patch('questionnaire.utils.put_questionnaire_data')
    @patch('questionnaire.signals.change_status.send')
    def test_publish_updates_status(self, mock_change_status, mock_put_data,
                                    mock_messages):
        mock_put_data.return_value = None, []
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['publish_questionnaire'])
        self.obj.status = 3
        self.obj.code = 'code'
        self.obj.links.filter.return_value = []
        self.request.user = Mock()
        self.request.POST = {'publish': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(self.obj.status, 4)
        mock_messages.success.assert_called_once_with(
            self.request,
            'The questionnaire was successfully set public.')

    @patch('questionnaire.utils.put_questionnaire_data')
    @patch('questionnaire.signals.change_status.send')
    def test_publish_calls_put_questionnaire_data(
            self, mock_change_status, mock_put_data, mock_messages):
        mock_put_data.return_value = None, []
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['publish_questionnaire'])
        self.obj.status = 3
        self.obj.code = 'code'
        self.obj.links.filter.return_value = []
        self.request.user = Mock()
        self.request.POST = {'publish': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        mock_put_data.assert_called_once_with('sample', [self.obj])

    @patch('questionnaire.utils.put_questionnaire_data')
    @patch('questionnaire.signals.change_status.send')
    def test_publish_calls_put_questionnaire_data_for_all_links(
            self, mock_change_status, mock_put_data, mock_messages):
        mock_put_data.return_value = None, []
        mock_link = Mock()
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['publish_questionnaire'])
        self.obj.links.filter.return_value = [mock_link]
        self.obj.status = 3
        self.obj.code = 'code'
        self.request.user = Mock()
        self.request.POST = {'publish': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        self.assertEqual(mock_put_data.call_count, 2)
        call_1 = call('sample', [self.obj])
        call_2 = call(
            mock_link.configurations.first.return_value.code, [mock_link])
        mock_put_data.assert_has_calls([call_1, call_2])

    def test_assign_needs_status(self, mock_messages):
        self.obj.status = 6
        self.request.POST = {'assign': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request,
            'No users can be assigned to this questionnaire because of its '
            'status.')

    def test_assign_needs_privileges(self, mock_messages):
        self.obj.status = 2
        self.request.POST = {'assign': 'foo'}
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request,
            'You do not have permissions to assign a user to this '
            'questionnaire.')

    def test_assign_handles_non_valid_ids(self, mock_messages):
        self.obj.status = 2
        self.request.POST = {
            'assign': 'foo',
            'user-id': 'foo,bar',
        }
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['assign_questionnaire'])
        self.obj.get_users_by_role.return_value = []
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.success.assert_called_once_with(
            self.request,
            'Assigned users were successfully updated')

    @patch('questionnaire.utils.typo3_client')
    @patch('questionnaire.signals.change_member.send')
    def test_assign_adds_new_user(self, mock_change_member, mock_typo3_client, mock_messages):
        self.obj.status = 2
        self.request.POST = {
            'assign': 'foo',
            'user-id': '98',
        }
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['assign_questionnaire'])
        self.obj.get_users_by_role.return_value = []
        mock_typo3_client.get_user_information.return_value = {
            'username': 'user'
        }
        handle_review_actions(self.request, self.obj, 'sample')
        user = User.objects.get(pk=98)
        self.obj.add_user.assert_called_once_with(user, 'reviewer')

        mock_messages.success.assert_called_once_with(
            self.request,
            'Assigned users were successfully updated')

    @patch('questionnaire.signals.change_member.send')
    def test_assign_removes_user(self, mock_change_member, mock_messages):
        self.obj.status = 2
        self.request.POST = {
            'assign': 'foo',
            'user-id': '98',
        }
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['assign_questionnaire'])
        mock_user = Mock()
        self.obj.get_users_by_role.return_value = [mock_user]
        handle_review_actions(self.request, self.obj, 'sample')
        self.obj.remove_user.assert_called_once_with(mock_user, 'reviewer')


@patch('questionnaire.utils.messages')
class UnccdFlagTest(TestCase):

    fixtures = ['groups_permissions', 'global_key_values', 'sample', 'unccd',
                'sample_questionnaires_5']

    def setUp(self):
        self.obj = Mock(spec=Questionnaire)
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=[])
        self.obj.links.all.return_value = []
        self.user = create_new_user()
        self.user.update(usergroups=[{
            'name': 'UNCCD Focal Point',
            'unccd_country': 'CHE',
        }])
        self.request = Mock()
        self.request.user = self.user
        self.request.POST = {'flag-unccd': 'foo'}

    def test_flag_unccd_requires_permissions(self, mock_messages):
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request, 'You do not have permissions to add this flag!')

    def test_flag_unccd_requires_valid_flag(self, mock_messages):
        Flag.objects.get(flag='unccd_bp').delete()
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['flag_unccd_questionnaire'])
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request, 'The flag could not be set.')

    def test_flag_unccd_prevented_if_review_questionnaire(self, mock_messages):
        # Create a copy of the questionnaire
        questionnaire = Questionnaire.objects.get(pk=1)
        questionnaire.pk = None
        questionnaire.status = 1
        questionnaire.save()
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request,
            'The flag could not be set because a version of this questionnaire '
            'is already in the review process and needs to be published first. '
            'Please try again later.')

    def test_flag_unccd_creates_a_new_version(self, mock_messages):
        questionnaire = Questionnaire.objects.get(pk=1)
        self.assertEqual(Questionnaire.objects.count(), 5)
        handle_review_actions(self.request, questionnaire, 'sample')
        self.assertEqual(Questionnaire.objects.count(), 6)

    def test_flag_unccd_creates_a_new_reviewed_version(self, mock_messages):
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        new_version = Questionnaire.objects.latest('id')
        self.assertEqual(new_version.status, 3)

    def test_flag_unccd_adds_flag(self, mock_messages):
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        new_version = Questionnaire.objects.latest('id')
        self.assertEqual(new_version.flags.count(), 1)

    def test_flag_unccd_adds_user(self, mock_messages):
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        new_version = Questionnaire.objects.latest('id')
        self.assertEqual(new_version.get_user(self.user, 'flagger'), self.user)

    def test_flag_unccd_adds_success_message(self, mock_messages):
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        mock_messages.success.assert_called_once_with(
            self.request, 'The flag was successfully set.')


@patch('questionnaire.utils.messages')
class UnccdUnflagTest(TestCase):

    fixtures = ['groups_permissions', 'global_key_values', 'sample', 'unccd',
                'sample_questionnaires_5']

    def setUp(self):
        self.obj = Mock(spec=Questionnaire)
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=[])
        self.obj.links.all.return_value = []
        self.user = create_new_user()
        self.user.update(usergroups=[{
            'name': 'UNCCD Focal Point',
            'unccd_country': 'CHE',
        }])
        self.request = Mock()
        self.request.user = self.user
        self.request.POST = {'unflag-unccd': 'foo'}
        self.questionnaire = Questionnaire.objects.get(pk=1)
        flag = Flag.objects.first()
        self.questionnaire.add_flag(flag)

    def test_unflag_unccd_requires_permissions(self, mock_messages):
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request, 'You do not have permissions to remove this flag!')

    def test_unflag_unccd_requires_valid_flag(self, mock_messages):
        Flag.objects.get(flag='unccd_bp').delete()
        RolesPermissions = namedtuple(
            'RolesPermissions', ['roles', 'permissions'])
        self.obj.get_roles_permissions.return_value = RolesPermissions(
            roles=[], permissions=['unflag_unccd_questionnaire'])
        handle_review_actions(self.request, self.obj, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request, 'The flag could not be removed.')

    def test_unflag_unccd_prevented_if_review_questionnaire(self, mock_messages):
        # Create a copy of the questionnaire
        questionnaire = Questionnaire.objects.get(pk=1)
        questionnaire.pk = None
        questionnaire.status = 1
        questionnaire.save()
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        mock_messages.error.assert_called_once_with(
            self.request,
            'The flag could not be removed because a version of this '
            'questionnaire is already in the review process and needs to be '
            'published first. Please try again later.')

    def test_unflag_unccd_creates_a_new_version(self, mock_messages):
        self.assertEqual(Questionnaire.objects.count(), 5)
        handle_review_actions(self.request, self.questionnaire, 'sample')
        self.assertEqual(Questionnaire.objects.count(), 6)

    def test_unflag_unccd_creates_a_new_reviewed_version(self, mock_messages):
        handle_review_actions(self.request, self.questionnaire, 'sample')
        new_version = Questionnaire.objects.latest('id')
        self.assertEqual(new_version.status, 3)

    def test_unflag_unccd_removes_flag(self, mock_messages):
        handle_review_actions(self.request, self.questionnaire, 'sample')
        new_version = Questionnaire.objects.latest('id')
        self.assertEqual(new_version.flags.count(), 0)

    def test_unflag_unccd_removes_user(self, mock_messages):
        questionnaire = Questionnaire.objects.get(pk=1)
        handle_review_actions(self.request, questionnaire, 'sample')
        new_version = Questionnaire.objects.latest('id')
        self.assertEqual(new_version.get_user(self.user, 'flagger'), None)

    def test_unflag_unccd_adds_success_message(self, mock_messages):
        handle_review_actions(self.request, self.questionnaire, 'sample')
        mock_messages.success.assert_called_once_with(
            self.request,
            'The flag was successfully removed. Please note that this created '
            'a new version which needs to be reviewed. In the meantime, you '
            'are seeing the public version which still shows the flag.')


class CompareQuestionnaireDataTest(TestCase):

    def setUp(self):
        self.data_1 = {
            'qg_1': [
                {
                    'key_1': {
                        'en': 'foo',
                        'fr': 'bar'
                    },
                    'key_2': 'asdf'
                }
            ],
            'qg_2': [
                {
                    'key_3': 1,
                    'key_4': ['faz', 'taz']
                }
            ],
            'qg_3': [
                {
                    'key_5': {
                        'en': 'foo'
                    }
                },
                {
                    'key_5': {
                        'en': 'bar'
                    }
                }
            ]
        }
        self.data_2 = copy.deepcopy(self.data_1)

    def test_no_difference(self):
        diff = compare_questionnaire_data(self.data_1, self.data_2)
        self.assertEqual(diff, [])

    def test_missing_qg_in_first(self):
        self.data_2.update({'qg_add': []})
        diff = compare_questionnaire_data(self.data_2, self.data_1)
        self.assertEqual(diff, ['qg_add'])

    def test_missing_qg_in_second(self):
        self.data_2.update({'qg_add': []})
        diff = compare_questionnaire_data(self.data_1, self.data_2)
        self.assertEqual(diff, ['qg_add'])

    def test_single_value_changed_in_first(self):
        self.data_2['qg_1'][0]['key_2'] = 'foo'
        diff = compare_questionnaire_data(self.data_2, self.data_1)
        self.assertEqual(diff, ['qg_1'])

    def test_single_value_changed_in_second(self):
        self.data_2['qg_1'][0]['key_2'] = 'foo'
        diff = compare_questionnaire_data(self.data_1, self.data_2)
        self.assertEqual(diff, ['qg_1'])

    def test_key_changed_in_first(self):
        self.data_2['qg_1'][0].update({'add': 'foo'})
        diff = compare_questionnaire_data(self.data_2, self.data_1)
        self.assertEqual(diff, ['qg_1'])

    def test_value_added(self):
        self.data_2['qg_2'][0]['key_4'].append('asdf')
        diff = compare_questionnaire_data(self.data_2, self.data_1)
        self.assertEqual(diff, ['qg_2'])
