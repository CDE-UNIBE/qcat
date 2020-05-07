import ast
import json
import logging
from uuid import UUID

from django.apps import apps
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.db.models.signals import pre_save
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.utils.functional import Promise
from django.utils.translation import ugettext as _, get_language

from accounts.client import remote_user_client
from accounts.models import User
from configuration.cache import get_configuration
from configuration.configuration import QuestionnaireQuestion, \
    QuestionnaireConfiguration
from configuration.utils import get_configuration_query_filter, \
    get_choices_from_model, get_choices_from_questiongroups
from qcat.errors import QuestionnaireFormatError
from questionnaire.errors import QuestionnaireLockedException
from questionnaire.receivers import prevent_updates_on_published_items
from questionnaire.serializers import QuestionnaireSerializer
from search.index import (
    put_questionnaire_data,
    delete_questionnaires_from_es,
)
from .conf import settings
from .models import Questionnaire, Flag, Lock
from .signals import change_status, change_member, delete_questionnaire

logger = logging.getLogger(__name__)


def validate_questionnaire_data(data, configuration, no_limit_check=False):
    """
    Validate a questionnaire data dictionary so it can be saved to the
    database. This namely removes all empty values and parses measured
    values to integers.

    This function can also be used to test if a questionnaire data
    dictionary is empty (if returned cleaned data = {}).

    Args:
        ``data`` (dict): A questionnaire data dictionary.

        ``configuration``
        (:class:`configuration.configuration.QuestionnaireConfiguration`):
        The configuration of the questionnaire to test the data against.

    Returns:
        ``dict``. The cleaned questionnaire data dictionary.

        ``list``. A list with errors encountered. Empty if the
        dictionary is valid.
    """
    errors = []
    cleaned_data = {}
    try:
        is_valid_questionnaire_format(data)
    except QuestionnaireFormatError as e:
        return cleaned_data, [str(e)]
    """
    Collect the questiongroup conditions. This can be done only once for
    all questiongroups for performance reasons.
    The conditions are collected in a dict of form:
    {
        "CONDITION_NAME": ("QG_KEYWORD", "Q_KEYWORD", ["COND_1", "COND_2"])
    }
    """
    questiongroup_conditions = {}
    for questiongroup in configuration.get_questiongroups():
        for question in questiongroup.questions:
            for conditions in question.questiongroup_conditions:
                condition, condition_name = conditions.split('|')
                if condition_name in questiongroup_conditions:
                    questiongroup_conditions[condition_name][2].append(
                        condition)
                else:
                    questiongroup_conditions[condition_name] = \
                        questiongroup.keyword, question.keyword, [condition]
    for qg_keyword, qg_data_list in data.items():
        questiongroup = configuration.get_questiongroup_by_keyword(qg_keyword)
        if questiongroup is None:
            # If the questiongroup is not part of the configuration raise error
            errors.append(
                "Questiongroup with keyword '{}' is not valid for this Configuration".format(
                    qg_keyword))
            continue
        if questiongroup.max_num < len(qg_data_list):
            errors.append(
                'Questiongroup with keyword "{}" has a max_num of {} but '
                'appears {} times'.format(
                    qg_keyword, questiongroup.max_num, len(qg_data_list)))
            continue
        if questiongroup.inherited_configuration:
            # Do not store linked questiongroups
            continue
        cleaned_qg_list = []
        ordered_qg = False
        for qg_data in qg_data_list:
            cleaned_qg = {}
            for key, value in qg_data.items():
                if not value and not isinstance(value, (bool, int)):
                    continue
                if key == '__order':
                    cleaned_qg['__order'] = value
                    continue
                question = questiongroup.get_question_by_key_keyword(key)
                if question is None:
                    errors.append(
                        'Question with keyword "{}" is not valid for '
                        'Questiongroup with keyword "{}"'.format(
                            key, qg_keyword))
                    continue
                if question.conditional:
                    for q in question.questiongroup.questions:
                        for c in q.conditions:
                            if key in c[2]:
                                cond_data = qg_data.get(q.keyword)
                                if not cond_data or c[0] not in cond_data:
                                    errors.append(
                                        'Key "{}" is only valid if "{}={}"'
                                        .format(key, q.keyword, c[0]))
                if question.field_type in ['measure']:
                    try:
                        value = int(value)
                    except ValueError:
                        errors.append(
                            'Measure value "{}" of key "{}" (questiongroup '
                            '"{}") is not valid.'.format(
                                value, key, qg_keyword))
                        continue
                if question.field_type in [
                        'bool', 'measure', 'select_type', 'select', 'radio',
                    'select_conditional_custom']:
                    if value not in [c[0] for c in question.choices]:
                        errors.append(
                            'Value "{}" is not valid for key "{}" ('
                            'questiongroup "{}").'.format(
                                value, key, qg_keyword))
                        continue
                elif question.field_type in [
                    'select_conditional_questiongroup']:
                    # This is checked later.
                    pass
                elif question.field_type in [
                        'checkbox', 'image_checkbox', 'cb_bool', 'multi_select']:
                    if not isinstance(value, list):
                        errors.append(
                            'Value "{}" of key "{}" needs to be a list'.format(
                                value, key))
                        continue
                    if question.field_type in ['cb_bool']:
                        try:
                            value = [int(v) for v in value]
                        except ValueError:
                            errors.append(
                                'Value "{}" is not a valid boolean checkbox '
                                'value for key "{}" (questiongroup "{}")'
                                .format(value, key, qg_keyword))
                            continue
                    for v in value:
                        if v not in [c[0] for c in question.choices]:
                            errors.append(
                                'Value "{}" is not valid for key "{}" ('
                                'questiongroup "{}").'.format(
                                    value, key, qg_keyword))
                            continue
                    max_cb = question.form_options.get('field_options', {}).get(
                        'data-cb-max-choices')
                    if max_cb and len(value) > max_cb:
                        errors.append('Key "{}" has too many values: {}'.format(
                            key, value))
                        continue
                elif question.field_type in ['char', 'text', 'wms_layer']:
                    if not isinstance(value, dict):
                        errors.append(
                            'Value "{}" of key "{}" needs to be a dict.'
                            .format(value, key))
                        continue
                    translations = {}
                    for locale, translation in value.items():
                        if translation:
                            if (not no_limit_check and question.max_length and
                                    len(translation) > question.max_length):

                                subcategory = questiongroup.get_top_subcategory()
                                subcategory_name = '{} {}'.format(
                                    subcategory.form_options.get('numbering'),
                                    subcategory.label)
                                error_msg = 'Value of question "{}" of ' \
                                            'subcategory "{}" is too long. It ' \
                                            'can only contain {} ' \
                                            'characters.'.format(
                                                question.label,
                                                subcategory_name,
                                                question.max_length)
                                errors.append(error_msg)
                                continue
                            translations[locale] = translation
                    value = translations
                elif question.field_type in ['int']:
                    try:
                        value = int(value)
                    except ValueError:
                        errors.append('Value "{}" of key "{}" is not a valid '
                                      'integer.'.format(value, key))
                        continue
                elif question.field_type in ['float']:
                    try:
                        value = float(value)
                    except ValueError:
                        errors.append('Value "{}" of key "{}" is not a valid '
                                      'number.'.format(value, key))
                        continue
                elif question.field_type in ['select_model']:
                    model = question.form_options.get('model')
                    choices = get_choices_from_model(model, only_active=False)
                    if str(value) not in [str(c[0]) for c in choices]:
                        errors.append('The value is not a valid choice of model'
                                      ' "{}"'.format(model))
                        continue
                    try:
                        value = int(value)
                    except TypeError:
                        value = None
                elif question.field_type in ['todo']:
                    value = None
                elif question.field_type in ['image', 'file', 'date']:
                    pass
                elif question.field_type in [
                        'user_id', 'link_id', 'hidden', 'display_only']:
                    pass
                elif question.field_type in ['link_video']:
                    # TODO: This should be properly checked!
                    pass
                elif question.field_type in ['map']:
                    # A very rough check if the value is a GeoJSON.
                    try:
                        geojson = json.loads(value)
                    except ValueError:
                        errors.append('Invalid geometry: "{}"'.format(value))
                        continue
                    for feature in geojson.get('features', []):
                        geom = feature.get('geometry', {})
                        if 'coordinates' not in geom or 'type' not in geom:
                            errors.append('Invalid geometry: "{}"'.format(value))
                            continue
                else:
                    raise NotImplementedError(
                        'Field type "{}" needs to be checked properly'.format(
                            question.field_type))
                if value or isinstance(value, (bool, int, float)):
                    cleaned_qg[key] = value
            if cleaned_qg:
                if len(cleaned_qg) == 1 and '__order' in cleaned_qg:
                    continue
                cleaned_qg_list.append(cleaned_qg)
                if '__order' in cleaned_qg:
                    ordered_qg = True
        if ordered_qg is True:
            cleaned_qg_list = sorted(
                cleaned_qg_list, key=lambda qg: qg.get('__order', 0))
        if cleaned_qg_list:
            cleaned_data[qg_keyword] = cleaned_qg_list
        if cleaned_qg_list and questiongroup.questiongroup_condition:
            condition_fulfilled = False
            for condition_name, condition_data in questiongroup_conditions.\
                    items():
                if condition_name != questiongroup.questiongroup_condition:
                    continue
                for qg_data in data.get(condition_data[0], []):
                    condition_value = qg_data.get(condition_data[1])
                    if isinstance(condition_value, list):
                        all_values_evaluated = False
                        for cond_value in condition_value:
                            evaluated = True
                            for c in condition_data[2]:
                                try:
                                    evaluated = evaluated and eval(
                                        '{}{}'.format(cond_value, c))
                                except NameError:
                                    evaluated = evaluated and eval(
                                        '"{}"{}'.format(cond_value, c))
                                except:
                                    evaluated = False
                                    continue
                            all_values_evaluated = (
                                all_values_evaluated or evaluated)
                        condition_fulfilled = (
                            condition_fulfilled or all_values_evaluated)
                    else:
                        evaluated = True
                        for c in condition_data[2]:
                            try:
                                evaluated = evaluated and eval('{}{}'.format(
                                    condition_value, c))
                            except NameError:
                                evaluated = evaluated and eval(
                                    '"{}"{}'.format(condition_value, c))
                            except:
                                evaluated = False
                                continue
                        condition_fulfilled = evaluated or condition_fulfilled
            if condition_fulfilled is False:
                errors.append(
                    'Questiongroup with keyword "{}" requires condition "{}".'.
                    format(
                        questiongroup.keyword,
                        questiongroup.questiongroup_condition))

    # Check for select_conditional_questiongroup questions. This needs to be
    # done after cleaning the data JSON as these questions depend on other
    # questiongroups. Empty questiongroups (eg. {'qg_42': [{'key_57': ''}], ...}
    # are now cleaned.
    for qg_keyword, cleaned_qg_list in cleaned_data.items():

        questiongroup = configuration.get_questiongroup_by_keyword(qg_keyword)
        if questiongroup is None:
            continue

        select_conditional_questiongroup_data_list = []
        select_conditional_questiongroup_found = False

        for qg_data in cleaned_qg_list:
            select_conditional_questiongroup_data = {}
            for key, value in qg_data.items():

                question = questiongroup.get_question_by_key_keyword(key)
                if question is None:
                    continue

                if question.field_type in ['select_conditional_questiongroup']:
                    select_conditional_questiongroup_found = True

                    # Set currently valid question choices
                    questiongroups = question.form_options.get(
                        'options_by_questiongroups', [])
                    question.choices = get_choices_from_questiongroups(
                        cleaned_data, questiongroups, configuration.keyword,
                        configuration.edition)

                    if value in [c[0] for c in question.choices]:
                        # Only copy values which are valid options.
                        select_conditional_questiongroup_data[key] = value

                else:
                    select_conditional_questiongroup_data[key] = value

            select_conditional_questiongroup_data_list.append(
                select_conditional_questiongroup_data)

        if select_conditional_questiongroup_found:
            cleaned_data[
                qg_keyword] = select_conditional_questiongroup_data_list

    return cleaned_data, errors


def clean_questionnaire_data(data, configuration, no_limit_check=False):
    """
    Clean a questionnaire data dictionary so it can be saved to the
    database. This namely removes all empty values and parses measured
    values to integers.

    This function can also be used to test if a questionnaire data
    dictionary is empty (if returned cleaned data = {}).

    Args:
        ``data`` (dict): A questionnaire data dictionary.

        ``configuration``
        (:class:`configuration.configuration.QuestionnaireConfiguration`):
        The configuration of the questionnaire to test the data against.

    Returns:
        ``dict``. The cleaned questionnaire data dictionary.

        ``list``. A list with errors encountered. Empty if the
        dictionary is valid.
    """
    errors = []
    cleaned_data = {}
    try:
        is_valid_questionnaire_format(data)
    except QuestionnaireFormatError as e:
        return cleaned_data, [str(e)]
    """
    Collect the questiongroup conditions. This can be done only once for
    all questiongroups for performance reasons.
    The conditions are collected in a dict of form:
    {
        "CONDITION_NAME": ("QG_KEYWORD", "Q_KEYWORD", ["COND_1", "COND_2"])
    }
    """
    questiongroup_conditions = {}
    for questiongroup in configuration.get_questiongroups():
        for question in questiongroup.questions:
            for conditions in question.questiongroup_conditions:
                condition, condition_name = conditions.split('|')
                if condition_name in questiongroup_conditions:
                    questiongroup_conditions[condition_name][2].append(
                        condition)
                else:
                    questiongroup_conditions[condition_name] = \
                        questiongroup.keyword, question.keyword, [condition]
    for qg_keyword, qg_data_list in data.items():
        questiongroup = configuration.get_questiongroup_by_keyword(qg_keyword)
        if questiongroup is None:
            # If the questiongroup is not part of the current configuration
            # (because the data is based on an old configuration or the
            # questionnaire also has other configurations - modules?), it is
            # stored as it is.
            cleaned_data[qg_keyword] = qg_data_list
            continue
        if questiongroup.max_num < len(qg_data_list):
            errors.append(
                'Questiongroup with keyword "{}" has a max_num of {} but '
                'appears {} times'.format(
                    qg_keyword, questiongroup.max_num, len(qg_data_list)))
            continue
        if questiongroup.inherited_configuration:
            # Do not store linked questiongroups
            continue
        cleaned_qg_list = []
        ordered_qg = False
        for qg_data in qg_data_list:
            cleaned_qg = {}
            for key, value in qg_data.items():
                if not value and not isinstance(value, (bool, int)):
                    continue
                if key == '__order':
                    cleaned_qg['__order'] = value
                    continue
                question = questiongroup.get_question_by_key_keyword(key)
                if question is None:
                    errors.append(
                        'Question with keyword "{}" is not valid for '
                        'Questiongroup with keyword "{}"'.format(
                            key, qg_keyword))
                    continue
                if question.conditional:
                    for q in question.questiongroup.questions:
                        for c in q.conditions:
                            if key in c[2]:
                                cond_data = qg_data.get(q.keyword)
                                if not cond_data or c[0] not in cond_data:
                                    errors.append(
                                        'Key "{}" is only valid if "{}={}"'
                                        .format(key, q.keyword, c[0]))
                if question.field_type in ['measure']:
                    try:
                        value = int(value)
                    except ValueError:
                        errors.append(
                            'Measure value "{}" of key "{}" (questiongroup '
                            '"{}") is not valid.'.format(
                                value, key, qg_keyword))
                        continue
                if question.field_type in [
                        'bool', 'measure', 'select_type', 'select', 'radio',
                    'select_conditional_custom']:
                    if value not in [c[0] for c in question.choices]:
                        errors.append(
                            'Value "{}" is not valid for key "{}" ('
                            'questiongroup "{}").'.format(
                                value, key, qg_keyword))
                        continue
                elif question.field_type in [
                    'select_conditional_questiongroup']:
                    # This is checked later.
                    pass
                elif question.field_type in [
                        'checkbox', 'image_checkbox', 'cb_bool', 'multi_select']:
                    if not isinstance(value, list):
                        errors.append(
                            'Value "{}" of key "{}" needs to be a list'.format(
                                value, key))
                        continue
                    if question.field_type in ['cb_bool']:
                        try:
                            value = [int(v) for v in value]
                        except ValueError:
                            errors.append(
                                'Value "{}" is not a valid boolean checkbox '
                                'value for key "{}" (questiongroup "{}")'
                                .format(value, key, qg_keyword))
                            continue
                    for v in value:
                        if v not in [c[0] for c in question.choices]:
                            errors.append(
                                'Value "{}" is not valid for key "{}" ('
                                'questiongroup "{}").'.format(
                                    value, key, qg_keyword))
                            continue
                    max_cb = question.form_options.get('field_options', {}).get(
                        'data-cb-max-choices')
                    if max_cb and len(value) > max_cb:
                        errors.append('Key "{}" has too many values: {}'.format(
                            key, value))
                        continue
                elif question.field_type in ['char', 'text', 'wms_layer']:
                    if not isinstance(value, dict):
                        errors.append(
                            'Value "{}" of key "{}" needs to be a dict.'
                            .format(value, key))
                        continue
                    translations = {}
                    for locale, translation in value.items():
                        if translation:
                            if (not no_limit_check and question.max_length and
                                    len(translation) > question.max_length):

                                subcategory = questiongroup.get_top_subcategory()
                                subcategory_name = '{} {}'.format(
                                    subcategory.form_options.get('numbering'),
                                    subcategory.label)
                                error_msg = 'Value of question "{}" of ' \
                                            'subcategory "{}" is too long. It ' \
                                            'can only contain {} ' \
                                            'characters.'.format(
                                                question.label,
                                                subcategory_name,
                                                question.max_length)
                                errors.append(error_msg)
                                continue
                            translations[locale] = translation
                    value = translations
                elif question.field_type in ['int']:
                    try:
                        value = int(value)
                    except ValueError:
                        errors.append('Value "{}" of key "{}" is not a valid '
                                      'integer.'.format(value, key))
                        continue
                elif question.field_type in ['float']:
                    try:
                        value = float(value)
                    except ValueError:
                        errors.append('Value "{}" of key "{}" is not a valid '
                                      'number.'.format(value, key))
                        continue
                elif question.field_type in ['select_model']:
                    model = question.form_options.get('model')
                    choices = get_choices_from_model(model, only_active=False)
                    if str(value) not in [str(c[0]) for c in choices]:
                        errors.append('The value is not a valid choice of model'
                                      ' "{}"'.format(model))
                        continue
                    try:
                        value = int(value)
                    except TypeError:
                        value = None
                elif question.field_type in ['todo']:
                    value = None
                elif question.field_type in ['image', 'file', 'date']:
                    pass
                elif question.field_type in [
                        'user_id', 'link_id', 'hidden', 'display_only']:
                    pass
                elif question.field_type in ['link_video']:
                    # TODO: This should be properly checked!
                    pass
                elif question.field_type in ['map']:
                    # A very rough check if the value is a GeoJSON.
                    try:
                        geojson = json.loads(value)
                    except ValueError:
                        errors.append('Invalid geometry: "{}"'.format(value))
                        continue
                    for feature in geojson.get('features', []):
                        geom = feature.get('geometry', {})
                        if 'coordinates' not in geom or 'type' not in geom:
                            errors.append('Invalid geometry: "{}"'.format(value))
                            continue
                else:
                    raise NotImplementedError(
                        'Field type "{}" needs to be checked properly'.format(
                            question.field_type))
                if value or isinstance(value, (bool, int, float)):
                    cleaned_qg[key] = value
            if cleaned_qg:
                if len(cleaned_qg) == 1 and '__order' in cleaned_qg:
                    continue
                cleaned_qg_list.append(cleaned_qg)
                if '__order' in cleaned_qg:
                    ordered_qg = True
        if ordered_qg is True:
            cleaned_qg_list = sorted(
                cleaned_qg_list, key=lambda qg: qg.get('__order', 0))
        if cleaned_qg_list:
            cleaned_data[qg_keyword] = cleaned_qg_list
        if cleaned_qg_list and questiongroup.questiongroup_condition:
            condition_fulfilled = False
            for condition_name, condition_data in questiongroup_conditions.\
                    items():
                if condition_name != questiongroup.questiongroup_condition:
                    continue
                for qg_data in data.get(condition_data[0], []):
                    condition_value = qg_data.get(condition_data[1])
                    if isinstance(condition_value, list):
                        all_values_evaluated = False
                        for cond_value in condition_value:
                            evaluated = True
                            for c in condition_data[2]:
                                try:
                                    evaluated = evaluated and eval(
                                        '{}{}'.format(cond_value, c))
                                except NameError:
                                    evaluated = evaluated and eval(
                                        '"{}"{}'.format(cond_value, c))
                                except:
                                    evaluated = False
                                    continue
                            all_values_evaluated = (
                                all_values_evaluated or evaluated)
                        condition_fulfilled = (
                            condition_fulfilled or all_values_evaluated)
                    else:
                        evaluated = True
                        for c in condition_data[2]:
                            try:
                                evaluated = evaluated and eval('{}{}'.format(
                                    condition_value, c))
                            except NameError:
                                evaluated = evaluated and eval(
                                    '"{}"{}'.format(condition_value, c))
                            except:
                                evaluated = False
                                continue
                        condition_fulfilled = evaluated or condition_fulfilled
            if condition_fulfilled is False:
                errors.append(
                    'Questiongroup with keyword "{}" requires condition "{}".'.
                    format(
                        questiongroup.keyword,
                        questiongroup.questiongroup_condition))

    # Check for select_conditional_questiongroup questions. This needs to be
    # done after cleaning the data JSON as these questions depend on other
    # questiongroups. Empty questiongroups (eg. {'qg_42': [{'key_57': ''}], ...}
    # are now cleaned.
    for qg_keyword, cleaned_qg_list in cleaned_data.items():

        questiongroup = configuration.get_questiongroup_by_keyword(qg_keyword)
        if questiongroup is None:
            continue

        select_conditional_questiongroup_data_list = []
        select_conditional_questiongroup_found = False

        for qg_data in cleaned_qg_list:
            select_conditional_questiongroup_data = {}
            for key, value in qg_data.items():

                question = questiongroup.get_question_by_key_keyword(key)
                if question is None:
                    continue

                if question.field_type in ['select_conditional_questiongroup']:
                    select_conditional_questiongroup_found = True

                    # Set currently valid question choices
                    questiongroups = question.form_options.get(
                        'options_by_questiongroups', [])
                    question.choices = get_choices_from_questiongroups(
                        cleaned_data, questiongroups, configuration.keyword,
                        configuration.edition)

                    if value in [c[0] for c in question.choices]:
                        # Only copy values which are valid options.
                        select_conditional_questiongroup_data[key] = value

                else:
                    select_conditional_questiongroup_data[key] = value

            select_conditional_questiongroup_data_list.append(
                select_conditional_questiongroup_data)

        if select_conditional_questiongroup_found:
            cleaned_data[
                qg_keyword] = select_conditional_questiongroup_data_list

    return cleaned_data, errors


def is_valid_questionnaire_format(questionnaire_data):
    """
    Helper function to check if the data of a questionnaire is valid or
    not.

    Args:
        ``questionnaire_data`` (dict): A questionnaire data dictionary.

    Returns:
        ``bool``. ``True`` if the dictionary is a valid questionnaire
        data.

    Raises:
        ``qcat.errors.QuestionnaireFormatError``
    """
    if not isinstance(questionnaire_data, dict):
        raise QuestionnaireFormatError(questionnaire_data)
    for k, v in questionnaire_data.items():
        if not isinstance(v, list):
            raise QuestionnaireFormatError(questionnaire_data)
    return True


def get_questionnaire_data_in_single_language(
        questionnaire_data, locale, original_locale=None):
    """
    Returns a questionnaire data dictionary in a single language. For
    translated values, the dictionary value containing the translations
    is replaced by a single string value with the translation in the
    given language.

    Example::

        # Input:
        {
          "qg_1": [
            {
              "key": {
                "en": "value_en",
                "es": "value_es"
              }
            }
          ]
        }

        # Output with locale=es
        {
          "qg_1": [
            {
              "key": "value_es"
            }
          ]
        }

    Args:
        ``questionnaire_data`` (dict): A questionnaire data dictionary.

        ``locale`` (str): The locale to find the translations for.

    Returns:
        ``dict``. The questionnaire data dictionary, without
        translations.
    """
    is_valid_questionnaire_format(questionnaire_data)
    data_sl = {}
    for questiongroup_keyword, questiongroups in questionnaire_data.items():
        qg_sl = []
        for questiongroup_data in questiongroups:
            qg_data_sl = {}
            for key, value in questiongroup_data.items():
                if isinstance(value, dict):
                    qg_data_sl[key] = value.get(
                        locale, value.get(original_locale))
                else:
                    qg_data_sl[key] = value
            qg_sl.append(qg_data_sl)
        data_sl[questiongroup_keyword] = qg_sl
    return data_sl


def get_questionnaire_data_for_translation_form(
        questionnaire_data, current_locale, original_locale):
    """
    Returns a questionnaire data dictionary which can be used in the
    form for translation. Each translated value is replaced by three keys:

    1. ``{"old_key": {...}}``: Contains all existing translations
    2. ``{"translation_key": "value"}``: Contains the translation in the
       current locale
    3. ``{"original_key": "value"}``: Contains the value as it was first
       entered in the original local.

    Example::

        # Input
        {
          "qg_1": [
            {
              "key_1": {
                "en": "value_en",
                "es": "value_es"
              }
            }
          ]
        }

        # Output with original_locale=en and current_locale=es
        {
          "qg_1": [
            {
              "old_key_1": {
                "en": "value_en",
                "es": "value_es"
              },
              "translation_key_1": "value_es",
              "original_key_1": "value_en"
            }
          ]
        }

    Args:
        ``questionnaire_data`` (dict): A questionnaire data dictionary.

        ``current_locale`` (str): The currently active locale.

        ``original_locale`` (str): The original locale in which the
        values were entered.

    Returns:
        ``dict``. The questionnaire data dictionary, with additional
        translation form fields.
    """
    is_valid_questionnaire_format(questionnaire_data)
    translation_prefix = QuestionnaireQuestion.translation_translation_prefix
    original_prefix = QuestionnaireQuestion.translation_original_prefix
    old_prefix = QuestionnaireQuestion.translation_old_prefix
    if original_locale is None:
        original_locale = current_locale
    data_translation = {}
    for questiongroup_keyword, questiongroups in questionnaire_data.items():
        qg_translation = []
        for questiongroup_data in questiongroups:
            qg_data_translation = {}
            for key, value in questiongroup_data.items():
                if isinstance(value, dict):
                    qg_data_translation['{}{}'.format(
                        translation_prefix, key)] = value.get(
                            current_locale, value.get(original_locale))
                    qg_data_translation['{}{}'.format(
                        original_prefix, key)] = value.get(original_locale)
                    qg_data_translation['{}{}'.format(old_prefix, key)] = value
                else:
                    qg_data_translation[key] = value
            qg_translation.append(qg_data_translation)
        data_translation[questiongroup_keyword] = qg_translation
    return data_translation


def get_questiongroup_data_from_translation_form(
        questiongroup_data, current_locale, original_locale):
    """
    Returns a cleaned questiongroup data dictionary from a dict in the
    translation form format. New translations will overwrite old
    translations stored in the hidden field.

    .. seealso::
        :func:`get_questionnaire_data_for_translation_form` for the
        format of the translation form dictionary.

    Args:
        ``questiongroup_data`` (dict): A data dictionary of a single
        questiongroup.

        ``current_locale`` (str): The currently active locale.

        ``original_locale`` (str): The original locale in which the
        values were entered.

    Returns:
        ``dict``. The questiongroup data dictionary with translations as
        it can be stored in the database.
    """
    translation_prefix = QuestionnaireQuestion.translation_translation_prefix
    original_prefix = QuestionnaireQuestion.translation_original_prefix
    old_prefix = QuestionnaireQuestion.translation_old_prefix
    if original_locale is None:
        original_locale = current_locale

    questiongroup_data_cleaned = {}
    # Collect the old translations and parse them to a dict
    for key, value in questiongroup_data.items():
        if not key.startswith(old_prefix):
            continue
        k = key.replace(old_prefix, '')
        try:
            questiongroup_data_cleaned[k] = ast.literal_eval(value)
        except:
            questiongroup_data_cleaned[k] = value

    # Collect the originals and translations and update the old
    # translations
    for key, value in questiongroup_data.items():
        if key.startswith(old_prefix):
            continue
        if key.startswith(translation_prefix):
            k = key.replace(translation_prefix, '', 1)
            if not isinstance(questiongroup_data_cleaned[k], dict):
                questiongroup_data_cleaned[k] = {}
            questiongroup_data_cleaned[k].update({current_locale: value})
        elif key.startswith(original_prefix):
            k = key.replace(original_prefix, '', 1)
            if not isinstance(questiongroup_data_cleaned[k], dict):
                questiongroup_data_cleaned[k] = {}
            questiongroup_data_cleaned[k].update({original_locale: value})
        else:
            questiongroup_data_cleaned[key] = value

    return questiongroup_data_cleaned


def get_active_filters(
        questionnaire_configuration: QuestionnaireConfiguration,
        query_dict: dict) -> list:
    """
    Get the currently active filters based on the query dict (eg. from
    the request). Only valid filters (correct format, based on
    questiongroups and keys of current configuration) are respected.
    The query dict can contain multiple keys with the same names.

    The current format of a filter is::

        filter__[questiongroup]__[key]=[value]

    Example::

        filter__qg_11__key_14=value_14_1

    Some filters can also be set with a different format. These are:

    * ``q``: A search term for the full text search (``q=search``)

    * ``created`` or ``updated``: A range of two comma-separated years
      (``created=2014,2016`` or ``updated=2015,2015``)

    All the options can also be combined, such as::

        q=search&filter__qg_11__key_14=value_14_1

    Args:
        ``questionnaire_configuration``
        (:class:`configuration.configuration.QuestionnaireConfiguration`):
        A questionnaire configurations.

        ``query_dict`` (Nested Multidict): A nested multidict object,
        eg. ``request.GET``.

    Returns:
        ``list``. A list of dictionaries with the active and valid
        filters. Each dictionary contains the following entries:

        - ``questiongroup``: The keyword of the questiongroup. For
          ``q``, this is set to ``_search``.

        - ``key``: The keyword of the key. For ``q``, this is set to
          ``_search``.

        - ``key_label``: The label of the key. For ``q``, this is set to
          "Search Terms".

        - ``value``: The keyword of the value.

        - ``value_label``: The label of the value if available. Else the
          value as provided in the filter is returned.

        - ``type``: The field type of the key. For ``q``, this is set to
          ``_search``.
    """
    active_filters = []
    for filter_param, filter_values in query_dict.lists():

        if filter_param == 'type':
            for filter_value in filter_values:
                if filter_value == 'wocat':
                    # Do not add type 'wocat' (= All SLM Data) to active
                    # filters.
                    continue
                active_filters.append({
                    'type': '_type',
                    'key': 'type',
                    'key_label': _('SLM Data'),
                    'operator': None,
                    'value': filter_value,
                    'value_label': dict(settings.QUESTIONNAIRE_SLM_DATA_TYPES).get(filter_value, filter_value),
                    'questiongroup': '_type',
                })
            continue

        if filter_param == 'q':
            for filter_value in filter_values:
                active_filters.append({
                    'type': '_search',
                    'key': '_search',
                    'key_label': _('Search Terms'),
                    'operator': None,
                    'value': filter_value,
                    'value_label': filter_value,
                    'questiongroup': '_search',
                })
            continue

        if filter_param in ['created', 'updated']:
            years = []
            for filter_value in filter_values:
                for y in filter_value.split('-'):
                    try:
                        years.append(int(y))
                    except ValueError:
                        pass
            if len(years) != 2:
                continue

            label = ''
            if filter_param == 'created':
                label = _('Created')
            elif filter_param == 'updated':
                label = _('Updated')

            active_filters.append({
                'type': '_date',
                'key': filter_param,
                'key_label': label,
                'operator': None,
                'value': '-'.join(str(y) for y in sorted(years)),
                'value_label': ' - '.join(str(y) for y in sorted(years)),
                'questiongroup': filter_param,
            })

        if filter_param in ['flag']:
            for filter_value in filter_values:
                try:
                    flag_label = Flag.objects.get(flag=filter_value)\
                        .get_flag_display()
                except Flag.DoesNotExist:
                    flag_label = _('Unknown')
                active_filters.append({
                    'type': '_flag',
                    'key': filter_param,
                    'key_label': '',
                    'operator': None,
                    'value': filter_value,
                    'value_label': flag_label,
                    'questiongroup': filter_param,
                })

        if filter_param in ['lang']:
            for filter_value in filter_values:
                active_filters.append({
                    'type': '_lang',
                    'key': filter_param,
                    'key_label': _('Language'),
                    'operator': None,
                    'value': filter_value,
                    'value_label': dict(settings.LANGUAGES).get(
                        filter_value, filter_value),
                    'questiongroup': filter_param,
                })

        if filter_param == 'edition':
            for filter_value in filter_values:
                active_filters.append({
                    'type': '_edition',
                    'key': filter_param,
                    'key_label': 'Edition',  # No translation: only used in API
                    'operator': None,
                    'value': filter_value,
                    'value_label': filter_value,
                    'questiongroup': filter_param,
                })

        if not filter_param.startswith('filter__'):
            continue

        params = filter_param.split('__')
        if len(params) not in [3, 4]:
            continue

        filter_questiongroup = params[1]
        filter_key = params[2]
        filter_operator = params[3] if len(params) == 4 else 'eq'

        question = questionnaire_configuration.get_question_by_keyword(
            filter_questiongroup, filter_key)

        if question is None:
            continue

        for filter_value in filter_values:

            # Each filter value can actually consist of multiple values
            # belonging to the same key, concatenated to a single string
            split_filter_values = filter_value.split('|')

            # Collect the labels of all values
            value_labels = []
            for single_filter_value in split_filter_values:
                value_label = next(
                    (v[1] for v in question.choices if str(v[0]) ==
                     single_filter_value),
                    filter_value)

                if question.field_type == 'select_model':
                    try:
                        model = apps.get_model(
                            app_label='configuration',
                            model_name=question.form_options.get('model'))
                        try:
                            obj = model.objects.get(pk=single_filter_value)
                            value_label = str(obj)
                        except (model.DoesNotExist, ValueError):
                            # If no object was found by ID or the value is not a
                            # valid ID, try to find the (supposed string) value
                            # in the name of the object.
                            filter_key = '{}_display'.format(filter_key)
                            value_label = single_filter_value
                    except LookupError:
                        continue

                value_labels.append(value_label)

            active_filters.append({
                'questiongroup': filter_questiongroup,
                'key': filter_key,
                'key_label': question.label_filter,
                'operator': filter_operator,
                'value': split_filter_values,
                'value_label': ' / '.join(value_labels),
                'type': question.field_type,
                'choices': question.choices,
            })

    return active_filters


def get_link_data(linked_objects, link_configuration_code=None):
    """
    Return a data representation (to be stored in the session or used in
    forms) of links retrieved from the database.

    Args:
        ``linked_objects`` (list of questionnaire.models.Questionnaire):
        A list of database model objects representing the linked
        Questionnaires.

    Kwargs:
        ``link_configuration_code`` (str): Optionally provide a
        configuration keyword for the link. If none is provided, the
        configuration is derived from the Questionnaire object.

    Returns:
        ``dict``. A dictionary containing the links grouped by
        link_configuration_code. The basic form of the dictionary is as
        follows::

            {
              "sample": [
                {
                  "id": 1,
                  "code": "code_of_questionnaire_with_id_1",
                  "name": "Name of Questionnaire with ID 1",
                  "configuration": "configuration_of_q"
                }
              ]
            }
    """
    links = {}
    for link in linked_objects:
        if link_configuration_code is None:
            link_configuration_code = link.configuration.code
        link_configuration = get_configuration(
            code=link_configuration_code,
            edition=link.configuration.edition)

        name_data = link_configuration.get_questionnaire_name(link.data)
        try:
            original_lang = link.questionnairetranslation_set.first().language
        except AttributeError:
            original_lang = None
        name = name_data.get(get_language(), name_data.get(original_lang, ''))

        link_list = links.get(link_configuration_code, [])

        if next((item for item in link_list if item['code'] == link.code),
                None) is not None:
            continue

        link_list.append({
            'id': link.id,
            'code': link.code,
            'name': name,
            'link': get_link_display(link_configuration_code, name, link.code),
            'configuration': link.configuration.code,
        })
        links[link_configuration_code] = link_list

    return links


def get_link_display(configuration_code, name, identifier):
    """
    Return the representation of a linked questionnaire used for display
    of the link. The display representation is the rendered template (
    ``/questionnaire/partial/link.html``) specific to the given
    configuration.

    Args:
        ``link_object`` (questionnaire.models.Questionnaire): The
        database model object of the linked Questionnaire.

        ``link_configuration`` (
        configuration.configuration.QuestionnaireConfiguration): The
        Configuration object of the linked Questionnaire.

    Returns:
        ``str``. The display representation of the link as rendered
        HTML.
    """
    link_template = '{}/questionnaire/partial/link.html'.format(
        configuration_code)
    link_route = '{}:questionnaire_details'.format(configuration_code)
    return render_to_string(link_template, {
        'name': name,
        'link_route': link_route,
        'questionnaire_identifier': identifier,
    })


def query_questionnaire(request, identifier):
    """
    Query and return a single Questionnaire.

    .. important::
        Note that this may return multiple Questionnaire objects, as
        there may be multiple versions for the same identifier.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``identifier`` (str): The identifier of the Questionnaire.

    Returns:
        ``django.db.models.query.QuerySet``. The queried
        Questionnaire(s).
    """

    # If the identifier is a valid UUID, the Questionnaire object is searched by
    # uuid, otherwise by code.
    try:
        UUID(identifier)
        q_filter = Q(uuid=identifier)
    except ValueError:
        q_filter = Q(code=identifier)

    status_filter = get_query_status_filter(request)

    return Questionnaire.with_status.not_deleted().filter(
        q_filter
    ).filter(
        status_filter
    )


def query_questionnaires(
        request, configuration_code, only_current=False, limit=10, offset=0,
        user=None, status_filter=None):
    """
    Query and return many Questionnaires.

    .. seealso::
        :func:`get_query_status_filter` for the status filters applied.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``configuration_code`` (str): The code of the questionnaire
        configuration.

    Kwargs:
        ``only_current`` (bool): A boolean indicating whether to include
        only questionnaires from the current configuration.

        ``limit`` (int): The limit of results the query will return.

        ``offset`` (int): The offset of the results of the query.

        ``user`` (accounts.models.User): If provided, add an additional
        filter to return only Questionnaires where the user is a member
        of.

        ``status_filter`` (django.db.models.Q): A Django filter object.
        If provided (not ``None``), this filter is used instead of the
        default ``status_filter`` (as provided by
        :func:`get_query_status_filter`).

    Returns:
        ``django.db.models.query.QuerySet``. The queried Questionnaires.
    """
    if status_filter is None:
        status_filter = get_query_status_filter(request)

    # Find the IDs of the Questionnaires which are visible to the
    # current user. If multiple versions exist for a Questionnaire, only
    # the latest (visible to the current user) is used.
    ids = Questionnaire.with_status.not_deleted().filter(
        get_configuration_query_filter(
            configuration_code, only_current=only_current),
        status_filter).values_list('id', flat=True).order_by(
            'code', '-updated').distinct('code')

    if user is not None:
        ids = ids.filter(members=user)

    query = Questionnaire.with_status.not_deleted().filter(id__in=ids)

    if limit is not None:
        return query[offset:offset + limit]

    return query


def get_query_status_filter(request):
    """
    Creates a filter object based on the statuses of the Questionnaires,
    to be used for database queries.

    The following status filters are applied:

    * Not logged in users always only see "public" Questionnaires.

    * Reviewers see all "submitted" and "public" Questionnaires.

    * Publishers see all "reviewed" and "public" Questionnaires.

    * Logged in users see all "public", as well as their own "draft",
      "submitted" and "reviewed" Questionnaires.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Returns:
        ``django.db.models.Q``. A Django filter object.
    """
    status_filter = Q()

    if request.user and request.user.is_authenticated():

        permissions = request.user.get_all_permissions()

        # If "view_questionnaire" is part of the permissions, return all
        # statuses
        if 'questionnaire.view_questionnaire' in permissions:
            return Q(status__in=[settings.QUESTIONNAIRE_DRAFT,
                                 settings.QUESTIONNAIRE_SUBMITTED,
                                 settings.QUESTIONNAIRE_REVIEWED,
                                 settings.QUESTIONNAIRE_PUBLIC])

        # Reviewers see all Questionnaires with status "submitted".
        if 'questionnaire.review_questionnaire' in permissions:
                status_filter |= Q(status__in=[settings.QUESTIONNAIRE_SUBMITTED])

        # Publishers see all Questionnaires with status "reviewed".
        if 'questionnaire.publish_questionnaire' in permissions:
            status_filter |= Q(status__in=[settings.QUESTIONNAIRE_REVIEWED])

        # Users see Questionnaires with status "draft", "submitted" and
        # "reviewed" if they are "compiler" or "editor".
        status_filter |= (
            Q(members=request.user) &
            Q(questionnairemembership__role__in=[
                settings.QUESTIONNAIRE_COMPILER, settings.QUESTIONNAIRE_EDITOR
            ])
            & Q(status__in=[settings.QUESTIONNAIRE_DRAFT,
                            settings.QUESTIONNAIRE_SUBMITTED,
                            settings.QUESTIONNAIRE_REVIEWED
                            ])
        )

        # Users see Questionnaires with status "submitted" if they are
        # assigned as "reviewer" for this Questionnaire. Reviewers also
        # see the "reviewed" Questionnaires they approved.
        status_filter |= (
            Q(members=request.user) &
            Q(questionnairemembership__role__in=[
                settings.QUESTIONNAIRE_REVIEWER
            ])
            & Q(status__in=[settings.QUESTIONNAIRE_SUBMITTED,
                            settings.QUESTIONNAIRE_REVIEWED]))

        # Users see Questionnaires with status "reviewed" if they are
        # assigned as "publisher" or as "flagger" for this Questionnaire.
        status_filter |= (
            Q(members=request.user) &
            Q(questionnairemembership__role__in=[
                settings.QUESTIONNAIRE_PUBLISHER,
                settings.QUESTIONNAIRE_FLAGGER,
            ])
            & Q(status__in=[settings.QUESTIONNAIRE_REVIEWED]))

    # Everybody sees Questionnaires with status "public".
    status_filter |= Q(status=settings.QUESTIONNAIRE_PUBLIC)

    return status_filter


def get_list_values(
        configuration_code=None, es_hits=None, questionnaire_objects=None,
        with_links=True, status_filter=None):
    """
    Retrieves and prepares data to be used in a list representation.
    Either handles a list of questionnaires retrieved from the database
    or searched with Elasticsearch.

    Kwargs:
        ``configuration_code`` (str): Optionally provide a configuration
        code which will be used for all items. This may result in some
        items not displaying any data if they are not shown in one of
        their configurations. If set to ``None``, the original
        configuration for each questionnaire is used to collect the list
        values.
        If ``configuration_code=wocat``, every item is rendered in its
        original configuration.

        ``es_search`` (dict): A dictionary as retrieved from an
        Elasticsearch query.

        ``questionnaire_objects`` (list): A list (queryset) of
        :class:`questionnaire.models.Questionnaire` models retrieved
        from the database.

        ``with_links`` (bool): A boolean indicating whether to return
        link data for the questionnaires or not. By default, for
        ``questionnaire_objects`` link data is queried from the
        database. If you do not want to query and display this
        information (eg. when displaying the links of a single
        questionnaire in the details page), set this to ``False``.

        ``status_filter`` (``django.db.models.Q``). A status filter for
        a given request. This needs to be specified if you
        ``questionnaire_objects`` are provided and ``with_links`` is
        ``True``.

        .. seealso:: :func:`get_query_status_filter`

    Returns:
        ``list``. A list of dictionaries containing the values needed
        for the list representation of Questionnaires. Along the values
        specified in the settings to appear in the list, some metadata
        is returned for each entry.
    """
    if es_hits is None:
        es_hits = []
    if questionnaire_objects is None:
        questionnaire_objects = []
    list_entries = []

    for result in es_hits:
        # Results from Elasticsearch. List values are already available.
        if result.get('_source'):

            serializer = QuestionnaireSerializer(
                data=result['_source']
            )

            if serializer.is_valid():
                serializer.to_list_values(lang=get_language())
                list_entries.append(serializer.validated_data)
            else:
                logger.warning('Invalid data on the serializer: {}'.format(serializer.errors))

    for obj in questionnaire_objects:
        # Results from database query. List values have to be retrieved
        # through the configuration of the questionnaires.
        template_value = {
            'list_data': obj.configuration_object.get_list_data([obj.data])[0]
        }

        metadata = obj.get_metadata()
        template_value.update(metadata)

        template_value = prepare_list_values(
            data=template_value, config=obj.configuration_object,
            lang=get_language()
        )

        # Reorder the links: Group them by linked configuration
        links = {}
        if with_links is True:
            link_data = get_link_data(obj.links.filter(status_filter))

            for questionnaire_configuration, link_dicts in link_data.items():
                for link_dict in link_dicts:
                    link_configuration = link_dict.get('configuration')
                    if link_configuration not in links:
                        links[link_configuration] = []
                    links[link_configuration].append(link_dict)

        template_value.update({
            'links': links,
            'id': obj.id,
            'url': obj.get_absolute_url(),
            'data': obj.data
        })
        list_entries.append(template_value)

    return list_entries


def handle_review_actions(request, questionnaire_object, configuration_code):
    """
    Handle review and form submission actions. Updates the Questionnaire
    object and adds a message.

    Completely overloaded method, handling too many cases, depending on
    request.POST values. The following cases are available:
    * submit: Change status from draft to submitted
    * review: Change status from submitted to reviewed
    * publish: Change status from reviewed to published, also put data in ES
    * reject: Change status from [submitted, reviewed] to draft
    * assign: Update the members (editors, reviewers, publishers) of a
        questionnaire
    * change-compiler: Change the compiler of the questionnaire
    * flag-unccd: Flag the questionnaire as one of UNCCD's cases
    * unflag-unccd: Unflag the questionnaire from being a UNCCD case
    * delete: Delete (set is_deleted) a questionnaire
    * new-version: Create a new (draft) version of a public questionnaire


    * "draft" Questionnaires can be submitted, sets them "submitted".

    * "submitted" Questionnaires can be reviewed, sets them "reviewed".

    * "reviewed" Questionnaires can be published, sets them "published".

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``questionnaire_object`` (questionnaire.models.Questionnaire):
        The Questionnaire object to update.

        ``configuration_code`` (string): The code of the current
        configuration. This is used when publishing a Questionnaire, in
        order to add it to Elasticsearch.

    Returns:
        ``None`` or ``HttpResponse``. Returns either a HttpResponse
        (typically a redirect) or None.
    """
    roles_permissions = questionnaire_object.get_roles_permissions(request.user)
    permissions = roles_permissions.permissions
    previous_status = questionnaire_object.status

    if request.POST.get('submit'):

        # Previous status must be "draft"
        if questionnaire_object.status != settings.QUESTIONNAIRE_DRAFT:
            messages.error(
                request, 'The questionnaire could not be submitted because it '
                'does not have to correct status.')
            return

        if 'submit_questionnaire' not in permissions:
            messages.error(
                request, 'The questionnaire could not be submitted because you'
                ' do not have permission to do so.')
            return

        # Update the status
        questionnaire_object.status = settings.QUESTIONNAIRE_SUBMITTED
        try:
            questionnaire_object.save()
        except QuestionnaireLockedException:
            # In case the questionnaire is still locked for the compiler, unlock
            # all previous logs
            Lock.objects.filter(
                user=request.user,
                questionnaire_code=questionnaire_object.code
            ).update(
                is_finished=True
            )
            questionnaire_object.save()

        messages.success(
            request, _('The questionnaire was successfully submitted.'))
        change_status.send(
            sender=settings.NOTIFICATIONS_CHANGE_STATUS,
            questionnaire=questionnaire_object,
            user=request.user,
            message=request.POST.get('message', ''),
            previous_status=previous_status
        )

    elif request.POST.get('review'):

        # Previous status must be "submitted"
        if questionnaire_object.status != settings.QUESTIONNAIRE_SUBMITTED:
            messages.error(
                request, 'The questionnaire could not be reviewed because '
                'it does not have to correct status.')
            return

        # Current user must be a reviewer
        if 'review_questionnaire' not in permissions:
            messages.error(
                request, 'The questionnaire could not be reviewed because '
                'you do not have permission to do so.')
            return

        # Attach the reviewer to the questionnaire if he is not already
        questionnaire_object.add_user(request.user, 'reviewer')

        # Update the status
        questionnaire_object.status = settings.QUESTIONNAIRE_REVIEWED

        try:
            questionnaire_object.save()
        except QuestionnaireLockedException as e:
            # If the same user also has a lock, then release this lock.
            if e.user == request.user:
                Lock.objects.filter(
                        user=request.user,
                        questionnaire_code=questionnaire_object.code
                    ).update(
                        is_finished=True
                    )
                questionnaire_object.save()
            else:
                return

        messages.success(
            request, _('The questionnaire was successfully reviewed.'))
        change_status.send(
            sender=settings.NOTIFICATIONS_CHANGE_STATUS,
            questionnaire=questionnaire_object,
            user=request.user,
            message=request.POST.get('message', ''),
            previous_status=previous_status
        )

    elif request.POST.get('publish'):

        # Previous status must be "reviewed"
        if questionnaire_object.status != settings.QUESTIONNAIRE_REVIEWED:
            messages.error(
                request, 'The questionnaire could not be published because '
                'it does not have to correct status.')
            return

        # Current user must be a publisher
        if 'publish_questionnaire' not in permissions:
            messages.error(
                request, 'The questionnaire could not be published because '
                'you do not have permission to do so.')
            return

        # Set the previously "public" Questionnaire to "inactive".
        # Also remove it from ES.
        previously_public = Questionnaire.objects.filter(
            code=questionnaire_object.code,
            status=settings.QUESTIONNAIRE_PUBLIC
        )
        for previous_object in previously_public:
            previous_object_previous_status = previous_object.status
            previous_object.status = settings.QUESTIONNAIRE_INACTIVE
            previous_object.save()
            delete_questionnaires_from_es([previous_object])
            change_status.send(
                sender=settings.NOTIFICATIONS_CHANGE_STATUS,
                questionnaire=previous_object,
                user=request.user,
                message=_('New version was published'),
                previous_status=previous_object_previous_status
            )

        # Update the status
        questionnaire_object.status = settings.QUESTIONNAIRE_PUBLIC

        try:
            questionnaire_object.save()
        except QuestionnaireLockedException as e:
            # If the same user also has a lock, then release this lock.
            if e.user == request.user:
                Lock.objects.filter(
                        user=request.user,
                        questionnaire_code=questionnaire_object.code
                    ).update(
                        is_finished=True
                    )
                questionnaire_object.save()
            else:
                return

        added, errors = put_questionnaire_data([questionnaire_object])

        # It is important to also put the data of the linked
        # questionnaires so changes (eg. name change) appear in their
        # links.
        # However, do this only where the linked questionnaire is "public"!
        # Otherwise, "draft" questionnaires would appear in the list.
        links_by_configuration = {}
        for link in questionnaire_object.links.filter(
                status=settings.QUESTIONNAIRE_PUBLIC):
            configuration_object = link.configuration
            if configuration_object.code not in links_by_configuration:
                links_by_configuration[configuration_object.code] = []
            links_by_configuration[configuration_object.code].append(link)

        for link_configuration, links in links_by_configuration.items():
            added, errors = put_questionnaire_data(links)

        messages.success(
            request, _('The questionnaire was successfully set public.'))
        change_status.send(
            sender=settings.NOTIFICATIONS_CHANGE_STATUS,
            questionnaire=questionnaire_object,
            user=request.user,
            message=request.POST.get('message', ''),
            previous_status=previous_status
        )

    elif request.POST.get('reject'):

        if questionnaire_object.status not in [
            settings.QUESTIONNAIRE_SUBMITTED, settings.QUESTIONNAIRE_REVIEWED
        ]:
            messages.error(
                request, 'The questionnaire could not be rejected because it '
                'does not have to correct status.')
            return

        if (questionnaire_object.status == settings.QUESTIONNAIRE_SUBMITTED
                and 'review_questionnaire' not in permissions):
            messages.error(
                request, 'The questionnaire could not be rejected because '
                'you do not have permission to do so.')
            return

        if (questionnaire_object.status == settings.QUESTIONNAIRE_REVIEWED
                and 'publish_questionnaire' not in permissions):
            messages.error(
                request, 'The questionnaire could not be rejected because '
                'you do not have permission to do so.')
            return

        # Attach the reviewer to the questionnaire if he is not already
        if questionnaire_object.status == settings.QUESTIONNAIRE_SUBMITTED:
            user_role = 'reviewer'
        else:
            user_role = 'publisher'
        questionnaire_object.add_user(request.user, user_role)

        # Update the status
        questionnaire_object.status = settings.QUESTIONNAIRE_DRAFT

        try:
            questionnaire_object.save()
        except QuestionnaireLockedException as e:
            # If the same user also has a lock, then release this lock.
            if e.user == request.user:
                Lock.objects.filter(
                        user=request.user,
                        questionnaire_code=questionnaire_object.code
                    ).update(
                        is_finished=True
                    )
                questionnaire_object.save()
            else:
                return

        messages.success(
            request, _('The questionnaire was successfully rejected.'))
        change_status.send(
            sender=settings.NOTIFICATIONS_CHANGE_STATUS,
            questionnaire=questionnaire_object,
            user=request.user,
            is_rejected=True,
            message=request.POST.get('reject-message', ''),
            previous_status=previous_status,
        )

        # Query the permissions again, if the user does not have
        # edit rights on the now draft questionnaire, then route him
        # back to home in order to prevent a 404 page.
        roles, permissions = questionnaire_object.get_roles_permissions(
            request.user)
        if 'edit_questionnaire' not in permissions:
            return redirect('wocat:home')

    elif request.POST.get('assign'):

        # Make sure the questionnaire has the right status and define the role
        # of the users based on the status.
        status = questionnaire_object.status
        if status == settings.QUESTIONNAIRE_DRAFT:
            role = settings.QUESTIONNAIRE_EDITOR
        elif status == settings.QUESTIONNAIRE_SUBMITTED:
            role = settings.QUESTIONNAIRE_REVIEWER
        elif status == settings.QUESTIONNAIRE_REVIEWED:
            role = settings.QUESTIONNAIRE_PUBLISHER
        else:
            messages.error(
                request, 'No users can be assigned to this questionnaire '
                         'because of its status.')
            return

        # Check privileges
        if 'assign_questionnaire' not in permissions:
            messages.error(
                request, 'You do not have permissions to assign a user to this '
                         'questionnaire.')
            return

        # Check the submitted user IDs
        user_ids_string = request.POST.get('user-id', '').split(',')
        try:
            user_ids = [int(i) for i in user_ids_string]
        except ValueError:
            user_ids = []

        previous_users = questionnaire_object.get_users_by_role(role)

        user_error = []
        for user_id in user_ids:
            # Create or update the user
            user_info = remote_user_client.get_user_information(user_id)
            if not user_info:
                user_error.append(user_id)
                continue

            # Get or create the user. Handle the case where a user has an email
            # address which is already in the database, but with a new ID.
            # This is the case if a user was deleted and re-created in the
            # remote WOCAT database, which in theory *should* not happen, but
            # (as history showed) cannot be ruled out.
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                try:
                    user = User.create_new(id=user_id, email=user_info['email'])
                except IntegrityError:
                    user_error.append(user_info)
                    continue
            remote_user_client.update_user(user, user_info)

            # Add the user
            questionnaire_object.add_user(user, role)
            if user not in previous_users:
                change_member.send(
                    sender=settings.NOTIFICATIONS_ADD_MEMBER,
                    questionnaire=questionnaire_object,
                    user=request.user,
                    affected=user,
                    role=role
                )

            # Remove user from list of previous users
            if user in previous_users:
                previous_users.remove(user)

        # Remove remaining previous users
        for user in previous_users:
            # send signal while user is still related.
            change_member.send(
                sender=settings.NOTIFICATIONS_REMOVE_MEMBER,
                questionnaire=questionnaire_object,
                user=request.user,
                affected=user,
                role=role
            )
            questionnaire_object.remove_user(user, role)

        if not user_error:
            messages.success(
                request,
                _('Assigned users were successfully updated'))

        else:
            messages.error(request, 'At least one of the assigned users could '
                                    'not be updated.')

    elif request.POST.get('change-compiler'):

        if 'change_compiler' not in permissions:
            messages.error(
                request, 'You do not have permissions to change the compiler!')
            return

        # Check the submitted user IDs
        user_ids_string = request.POST.get('compiler-id', '').split(',')

        if len(user_ids_string) > 1:
            messages.error(request, 'You can only choose one new compiler!')
            return

        try:
            user_id = int(user_ids_string[0])
        except ValueError:
            messages.error(request, 'No valid new compiler provided!')
            return

        # Create or update the user
        user_info = remote_user_client.get_user_information(user_id)
        if not user_info:
            messages.error(
                request,
                'No user information found for user {}'.format(user_id))
            return

        # Get or create the user. Handle the case where a user has an email
        # address which is already in the database, but with a new ID.
        # This is the case if a user was deleted and re-created in the
        # remote WOCAT database, which in theory *should* not happen, but
        # (as history showed) cannot be ruled out.
        try:
            new_compiler = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            try:
                new_compiler = User.create_new(id=user_id, email=user_info['email'])
            except IntegrityError:
                messages.error(
                    request, 'A user with this email address exists already.')
                return
        remote_user_client.update_user(new_compiler, user_info)

        role_compiler = settings.QUESTIONNAIRE_COMPILER

        # Get old compiler(s) -> there should always only be 1
        previous_compilers = questionnaire_object.get_users_by_role(
            role_compiler)

        # Do not do anything if the new compiler is already the old compiler.
        if previous_compilers == [new_compiler]:
            messages.info(request, 'This user is already the compiler.')
            return

        # Remove old compiler
        for pc in previous_compilers:
            change_member.send(
                sender=settings.NOTIFICATIONS_REMOVE_MEMBER,
                questionnaire=questionnaire_object,
                user=request.user,
                affected=pc,
                role=role_compiler
            )
            questionnaire_object.remove_user(pc, role_compiler)

        # Add new compiler
        questionnaire_object.add_user(new_compiler, role_compiler)
        change_member.send(
            sender=settings.NOTIFICATIONS_ADD_MEMBER,
            questionnaire=questionnaire_object,
            user=request.user,
            affected=new_compiler,
            role=role_compiler
        )

        keep_as_editor = request.POST.get('change-compiler-keep-editor')
        if keep_as_editor is not None:
            # Keep the previous compiler as editor
            role_editor = settings.QUESTIONNAIRE_EDITOR
            editors = questionnaire_object.get_users_by_role(role_editor)
            for pc in previous_compilers:
                # Do not add again if already an editor
                if pc in editors:
                    continue
                questionnaire_object.add_user(pc, role_editor)
                change_member.send(
                    sender=settings.NOTIFICATIONS_ADD_MEMBER,
                    questionnaire=questionnaire_object,
                    user=request.user,
                    affected=pc,
                    role=role_editor
                )

        # Re-add the questionnaire to ES if it was public
        if questionnaire_object.status == settings.QUESTIONNAIRE_PUBLIC:
            delete_questionnaires_from_es([questionnaire_object])
            added, errors = put_questionnaire_data([questionnaire_object])

        messages.success(request, 'Compiler was changed successfully')

    elif request.POST.get('flag-unccd'):

        if 'flag_unccd_questionnaire' not in permissions:
            messages.error(
                request, 'You do not have permissions to add this flag!')
            return

        try:
            flag = Flag.objects.get(flag=settings.QUESTIONNAIRE_FLAG_UNCCD)
        except Flag.DoesNotExist:
            messages.error(request, 'The flag could not be set.')
            return

        # No flag can be set if the Questionnaire has a version in the review
        # process.
        review_questionnaires = Questionnaire.objects.filter(
            code=questionnaire_object.code,
            status__in=[settings.QUESTIONNAIRE_DRAFT,
                        settings.QUESTIONNAIRE_SUBMITTED,
                        settings.QUESTIONNAIRE_REVIEWED]).all()
        if review_questionnaires:
            messages.error(request, _(
                'The flag could not be set because a version of this '
                'questionnaire is already in the review process and needs to '
                'be published first. Please try again later.'))
            return

        # First, create a new Questionnaire version
        compiler = questionnaire_object.get_users_by_role('compiler')[0]
        configuration = questionnaire_object.configuration
        next_status = settings.QUESTIONNAIRE_REVIEWED
        new_version = Questionnaire.create_new(
            configuration.code, questionnaire_object.data, compiler,
            previous_version=questionnaire_object, status=next_status,
            old_data=questionnaire_object.data)

        # Then flag it
        new_version.add_flag(flag)

        # todo: if this feature is used, add a notification.

        # Add the user who flagged it
        new_version.add_user(request.user, settings.QUESTIONNAIRE_FLAGGER)

        messages.success(request, _('The flag was successfully set.'))

    elif request.POST.get('unflag-unccd'):

        if 'unflag_unccd_questionnaire' not in permissions:
            messages.error(
                request, 'You do not have permissions to remove this flag!')
            return

        try:
            flag = Flag.objects.get(flag=settings.QUESTIONNAIRE_FLAG_UNCCD)
        except Flag.DoesNotExist:
            messages.error(request, 'The flag could not be removed.')
            return

        # No flag can be removed if the Questionnaire has a version in the
        # review process.
        review_questionnaires = Questionnaire.objects.filter(
            code=questionnaire_object.code,
            status__in=[settings.QUESTIONNAIRE_DRAFT,
                        settings.QUESTIONNAIRE_SUBMITTED,
                        settings.QUESTIONNAIRE_REVIEWED]).all()
        if review_questionnaires:
            messages.error(request, _(
                'The flag could not be removed because a version of this '
                'questionnaire is already in the review process and needs to '
                'be published first. Please try again later.'))
            return

        # First, create a new Questionnaire version
        compiler = questionnaire_object.get_users_by_role('compiler')[0]
        configuration = questionnaire_object.configuration
        next_status = settings.QUESTIONNAIRE_REVIEWED
        new_version = Questionnaire.create_new(
            configuration.code, questionnaire_object.data, compiler,
            previous_version=questionnaire_object, status=next_status,
            old_data=questionnaire_object.data)

        # Then remove the flag
        new_version.flags.remove(flag)

        # Remove the user who flagged it
        new_version.remove_user(request.user, settings.QUESTIONNAIRE_FLAGGER)

        messages.success(request, _(
            'The flag was successfully removed. Please note that this created '
            'a new version which needs to be reviewed. In the meantime, you '
            'are seeing the public version which still shows the flag.'))
        change_status.send(
            sender=settings.NOTIFICATIONS_CHANGE_STATUS,
            questionnaire=new_version,
            user=request.user,
            message=_('New version due to unccd flagging'),
            previous_status=previous_status
        )

    elif request.POST.get('delete'):
        if 'delete_questionnaire' not in permissions:
            messages.error(
                request,
                'You do not have permissions to delete this questionnaire!'
            )
            return

        if questionnaire_object.status == settings.QUESTIONNAIRE_PUBLIC:
            pre_save.disconnect(
                prevent_updates_on_published_items, sender=Questionnaire)
        questionnaire_object.is_deleted = True

        try:
            questionnaire_object.save()
        except QuestionnaireLockedException as e:
            # If the same user also has a lock, then release this lock.
            if e.user == request.user:
                Lock.objects.filter(
                    user=request.user,
                    questionnaire_code=questionnaire_object.code
                ).update(
                    is_finished=True
                )
                questionnaire_object.save()
            else:
                return

        if questionnaire_object.status == settings.QUESTIONNAIRE_PUBLIC:
            delete_questionnaires_from_es([questionnaire_object])
            pre_save.connect(
                prevent_updates_on_published_items, sender=Questionnaire)
        messages.success(request, _('The questionnaire was succesfully removed'))
        delete_questionnaire.send(
            sender=settings.NOTIFICATIONS_DELETE,
            questionnaire=questionnaire_object,
            user=request.user,
            previous_status=questionnaire_object.status
        )
        # Redirect to the overview of the user's questionnaires if there is no
        # other version of the questionnaire left to show.
        other_questionnaire = query_questionnaire(
            request, questionnaire_object.code).first()
        if other_questionnaire is None:
            return redirect('account_questionnaires')


def compare_questionnaire_data(data_1, data_2):
    """
    Compare two questionnaire data dictionaires and return the keywords
    of the questiongroups which are not identical.

    Args:
        ``data_1`` (dict): The first data dictionary.

        ``data_2`` (dict): The second data dictionary.

    Returns:
        ``list``. A list with the keywords of the questiongroups which
        are not identical.
    """
    # Check which questiongroups are only in one of the dicts.
    if data_1 is None:
        data_1 = {}
    if data_2 is None:
        data_2 = {}
    qg_keywords_1 = list(data_1.keys())
    qg_keywords_2 = list(data_2.keys())
    different_qg_keywords = list(set(qg_keywords_1).symmetric_difference(
        qg_keywords_2))

    # Compare the questiongroups appearing in both
    for qg_keyword, qg_data_1 in data_1.items():
        if qg_keyword in different_qg_keywords:
            continue
        pairs = zip(qg_data_1, data_2[qg_keyword])
        if any(x != y for x, y in pairs):
            different_qg_keywords.append(qg_keyword)

    return different_qg_keywords


def prepare_list_values(data, config, **kwargs):
    """
    Helper for the function: questionnaire.utils.get_list_values.
    This maps the 'new' serialized data as required by this 'old' function.
    Mapping is easier than to update all related templates.

    Args:
        data: dict
        config: configuration.QuestionnaireConfiguration
        **kwargs:

    Returns:
        dict

    """
    language = kwargs.get('lang')
    languages = dict(settings.LANGUAGES)

    # 'list_data' are set in the configuration. Make them directly
    # accessible. Use the language from the request - or the first
    # language from 'translations', which should be the original one.
    original_language = data.get('original_locale', 'en')

    for key, items in data['list_data'].items():
        # Items can either contain a dict with the language as key - or
        # a raw string (e.g. 'country')
        if isinstance(items, dict):
            data[key] = items.get(language, items.get(original_language))
        # lazy pgettext objects are Promise objects
        if isinstance(items, str) or isinstance(items, Promise):
            data[key] = items

    del data['list_data']

    if 'links' in data and isinstance(data['links'], dict):
        # TODO: Is this ever used anymore?
        data['links'] = data['links'].get(language, original_language)

    # Reorder the links: Group them by linked configuration
    links = {}
    for link in data.get('links', []):
        link_configuration = link.get('configuration')
        if link_configuration not in links:
            links[link_configuration] = []
        links[link_configuration].append(link)
    data['links'] = links

    # Get the display values of the translation languages
    if data['translations']:
        translations = []
        for lang in data['translations']:
            # 'translations' must not list the currently active language
            if lang in languages.keys():
                translations.append([lang, str(languages[lang])])
            else:
                translations.append([lang, lang])
        data['translations'] = translations

    data['configuration'] = config.keyword
    data['has_new_configuration_edition'] = config.has_new_edition
    return data
