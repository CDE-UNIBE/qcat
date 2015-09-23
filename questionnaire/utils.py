import ast
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _, get_language
from django.utils.dateparse import parse_datetime

from configuration.configuration import (
    QuestionnaireQuestion,
)
from configuration.utils import (
    ConfigurationList,
    get_configuration_query_filter,
)
from qcat.errors import QuestionnaireFormatError
from questionnaire.models import Questionnaire
from search.index import put_questionnaire_data


def clean_questionnaire_data(data, configuration, deep_clean=True, users=[]):
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
            errors.append(
                'Questiongroup with keyword "{}" does not exist'.format(
                    qg_keyword))
            continue
        if questiongroup.max_num < len(qg_data_list):
            errors.append(
                'Questiongroup with keyword "{}" has a max_num of {} but '
                'appears {} times'.format(
                    qg_keyword, questiongroup.max_num, len(qg_data_list)))
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
                        'bool', 'measure', 'select_type', 'select']:
                    if value not in [c[0] for c in question.choices]:
                        errors.append(
                            'Value "{}" is not valid for key "{}" ('
                            'questiongroup "{}").'.format(
                                value, key, qg_keyword))
                        continue
                elif question.field_type in [
                        'checkbox', 'image_checkbox', 'cb_bool']:
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
                elif question.field_type in ['char', 'text']:
                    if not isinstance(value, dict):
                        errors.append(
                            'Value "{}" of key "{}" needs to be a dict.'
                            .format(value, key))
                        continue
                    translations = {}
                    for locale, translation in value.items():
                        if translation:
                            if (question.max_length and
                                    len(translation) > question.max_length):
                                errors.append(
                                    'Value "{}" of key "{}" exceeds the '
                                    'max_length of {}.'.format(
                                        translation, key, question.max_length))
                                continue
                            translations[locale] = translation
                    value = translations
                elif question.field_type in ['todo']:
                    value = None
                elif question.field_type in ['image', 'user_display']:
                    pass
                elif question.field_type in ['user_id']:
                    pass
                else:
                    raise NotImplementedError(
                        'Field type "{}" needs to be checked properly'.format(
                            question.field_type))
                if value or isinstance(value, (bool, int)):
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


def get_questionnaire_data_in_single_language(questionnaire_data, locale):
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
                    qg_data_sl[key] = value.get(locale)
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
                        translation_prefix, key)] = value.get(current_locale)
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


def get_active_filters(questionnaire_configuration, query_dict):
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
        The questionnaire configuration.

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

        if filter_param == 'q':
            for filter_value in filter_values:
                active_filters.append({
                    'type': '_search',
                    'key': '_search',
                    'key_label': _('Search Terms'),
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
                'value': '-'.join(str(y) for y in sorted(years)),
                'value_label': ' - '.join(str(y) for y in sorted(years)),
                'questiongroup': filter_param,
            })

        if not filter_param.startswith('filter__'):
            continue

        params = filter_param.split('__')
        if len(params) != 3:
            continue

        filter_questiongroup = params[1]
        filter_key = params[2]

        question = questionnaire_configuration.get_question_by_keyword(
            filter_questiongroup, filter_key)

        if question is None:
            continue

        for filter_value in filter_values:
            value_label = next(
                (v[1] for v in question.choices if v[0] == filter_value),
                filter_value)

            active_filters.append({
                'questiongroup': filter_questiongroup,
                'key': filter_key,
                'key_label': question.label,
                'value': filter_value,
                'value_label': value_label,
                'type': question.field_type,
            })

    return sorted(active_filters, key=lambda k: k['key'])


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
                }
              ]
            }
    """
    configuration_list = ConfigurationList()
    links = {}
    for link in linked_objects:
        if link_configuration_code is None:
            link_configuration_code = link.configurations.first().code
        link_configuration = configuration_list.get(link_configuration_code)

        name_data = link_configuration.get_questionnaire_name(link.data)
        try:
            original_lang = link.questionnairetranslation_set.first().language
        except AttributeError:
            original_lang = None
        name = name_data.get(get_language(), name_data.get(original_lang, ''))

        link_list = links.get(link_configuration_code, [])
        link_list.append({
            'id': link.id,
            'code': link.code,
            'name': name,
            'link': get_link_display(link_configuration_code, name, link.code)
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
    status_filter = get_query_status_filter(request)

    return Questionnaire.objects.filter(code=identifier).filter(status_filter)


def query_questionnaires(
        request, configuration_code, only_current=False, limit=10, offset=0):
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

    Returns:
        ``django.db.models.query.QuerySet``. The queried Questionnaires.
    """
    status_filter = get_query_status_filter(request)

    # Find the IDs of the Questionnaires which are visible to the
    # current user. If multiple versions exist for a Questionnaire, only
    # the latest (visible to the current user) is used.
    ids = Questionnaire.objects.filter(
        get_configuration_query_filter(
            configuration_code, only_current=only_current),
        status_filter).values_list('id', flat=True).order_by(
            'code', '-updated').distinct('code')

    query = Questionnaire.objects.filter(id__in=ids)

    if limit is not None:
        return query[offset:offset+limit]

    return query


def get_query_status_filter(request):
    """
    Creates a filter object based on the statii of the Questionnaires,
    to be used for database queries.

    The following status filters are applied:

    * Not logged in users always only see "public" Questionnaires.

    * Moderators see all "pending" and "public" Questionnaires.

    * Logged in users see all "public", as well as their own "draft"
    and "pending" Questionnaires.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Returns:
        ``django.db.models.Q``. A Django filter object.
    """
    # Public always only sees "public"
    status_filter = Q(status=3)

    # Logged in users ...
    if request.user.is_authenticated():

        # ... see all "pending" and "public" if they are moderators,
        # along with their own "draft"
        if request.user.has_perm('questionnaire.can_moderate'):
            status_filter = (
                Q(status__in=[2, 3]) | (Q(members=request.user) & Q(status=1)))

        # ... see "public" and their own "draft" and "pending".
        else:
            status_filter = (
                Q(status=3) | (Q(members=request.user) & Q(status__in=[1, 2])))

    return status_filter


def query_questionnaires_for_link(configuration, q, limit=10):
    """
    Do a raw SQL search in the JSON data field of questionnaires. Only
    questionnaires of the configuration's keyword are returned. The
    search happens in the name field as defined by the parameter
    ``is_name`` in the configuration, searched in any language. The same
    term can also be used to search by code of the questionnaire.

    Args:
        ``configuration``
        (configuration.configuration.QuestionnaireConfiguration): The
        questionnaire configuration.

        ``q`` (str): The query string (to search either in the name or
        the code of the questionnaire).

    Kwargs:
        ``limit`` (int): Limit the number of results to return.

    Returns:

        ``int``. The total count of results encountered in the database.

        ``list``. The list of results. The length of this list may be
        smaller than the total count because of the limit applied.
    """
    question_keyword, questiongroup_keyword = configuration.get_name_keywords()
    if question_keyword is None or questiongroup_keyword is None:
        return 0, []

    query = """
        select questionnaire_questionnaire.id
        from questionnaire_questionnaire
            JOIN questionnaire_questionnaireconfiguration ON
                questionnaire_questionnaire.id =
                questionnaire_questionnaireconfiguration.questionnaire_id
            JOIN configuration_configuration ON
                questionnaire_questionnaireconfiguration.configuration_id =
                configuration_configuration.id
                AND configuration_configuration.code = %s,
        lateral jsonb_array_elements(
            questionnaire_questionnaire.data -> %s) questiongroup
        where """
    args = [configuration.keyword, questiongroup_keyword]

    languages = [l[0] for l in settings.LANGUAGES]
    for lang in languages:
        query += """
            questiongroup->%s->>'{}' ILIKE %s OR
        """.format(lang)
        args.extend([question_keyword, '%{}%'.format(q)])

    query += """
        questionnaire_questionnaire.code LIKE %s;
    """
    args.extend(['%{}%'.format(q)])

    results = Questionnaire.objects.raw(query, args)
    total = len(list(results))

    return total, results[:limit]


def get_list_values(
        configuration_code=None, es_hits=[], questionnaire_objects=[],
        with_links=True):
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

    Returns:
        ``list``. A list of dictionaries containing the values needed
        for the list representation of Questionnaires. Along the values
        specified in the settings to appear in the list, some metadata
        is returned for each entry.
    """
    list_entries = []

    for result in es_hits:
        # Results from Elasticsearch. List values are already available.

        # Fall back to the original configuration if viewed from "wocat"
        # or no configuration selected
        if configuration_code is None or configuration_code == 'wocat':
            current_configuration_code = result.get('_source', {}).get(
                'configurations', ['technologies'])[0]
        else:
            current_configuration_code = configuration_code

        template_value = result.get('_source', {}).get('list_data', {})

        translations = result.get('_source', {}).get('translations')
        if not isinstance(translations, list) or len(translations) == 0:
            translations = ['en']
        original_lang = translations[0]
        try:
            translations.remove(get_language())
        except ValueError:
            pass
        translations = [
            lang for lang in settings.LANGUAGES if lang[0] in translations]

        for key, value in template_value.items():
            if isinstance(value, dict):
                template_value[key] = value.get(
                    get_language(), value.get(original_lang))

        source = result.get('_source', {})
        configurations = source.get('configurations', [])

        template_value.update({
            'links': source.get('links', {}).get(get_language(), []),
            'configuration': current_configuration_code,  # Used for rendering
            'id': result.get('_id'),
            'configurations': configurations,
            'native_configuration': current_configuration_code in
            configurations,
            'created': parse_datetime(
                source.get('created', '')),
            'updated': parse_datetime(
                source.get('updated', '')),
            'translations': translations,
            'code': source.get('code', ''),
            'authors': source.get('authors', []),
        })
        list_entries.append(template_value)

    configuration_list = ConfigurationList()
    for obj in questionnaire_objects:
        # Results from database query. List values have to be retrieved
        # through the configuration of the questionnaires.

        # Fall back to the original configuration if viewed from "wocat"
        # or no configuration selected
        if configuration_code is None or configuration_code == 'wocat':
            configuration_object = obj.configurations.first()
            if configuration_object is not None:
                current_configuration_code = configuration_object.code
            else:
                current_configuration_code = 'technologies'
        else:
            current_configuration_code = configuration_code

        questionnaire_configuration = configuration_list.get(
            current_configuration_code)

        template_value = questionnaire_configuration.get_list_data(
            [obj.data])[0]

        metadata = obj.get_metadata()
        template_value.update(metadata)

        translations = metadata.get('translations', [])
        if len(translations) == 0:
            translations = ['en']
        original_lang = translations[0]
        try:
            translations.remove(get_language())
        except ValueError:
            pass
        translations = [
            lang for lang in settings.LANGUAGES if lang[0] in translations]

        for key, value in template_value.items():
            if isinstance(value, dict):
                template_value[key] = value.get(
                    get_language(), value.get(original_lang))

        links = []
        if with_links is True:
            link_data = get_link_data(obj.links.all())
            for configuration, link_dicts in link_data.items():
                links.extend([link.get('link') for link in link_dicts])

        template_value.update({
            'links': links,
            'configuration': current_configuration_code,  # Used for rendering
            'id': obj.id,
            'native_configuration': current_configuration_code in
            metadata.get('configurations', []),
            'translations': translations,
        })
        list_entries.append(template_value)

    return list_entries


def handle_review_actions(request, questionnaire_object, configuration_code):
    """
    Handle review and form submission actions. Updates the Questionnaire
    object and adds a message.

    * "draft" Questionnaires can be submitted, sets them "pending".

    * "pending" Questionnaires can be set public, sets them "public".

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``questionnaire_object`` (questionnaire.models.Questionnaire):
        The Questionnaire object to update.

        ``configuration_code`` (string): The code of the current
        configuration. This is used when publishing a Questionnaire, in
        order to add it to Elasticsearch.
    """
    if request.POST.get('submit'):

        # Previous status must be "draft"
        if questionnaire_object.status != 1:
            messages.error(
                request, 'The questionnaire could not be submitted because it '
                'does not have to correct status.')
            return

        # Current user must be the author of the questionnaire
        if request.user not in questionnaire_object.members.filter(
                questionnairemembership__role='author'):
            messages.error(
                request, 'The questionnaire could not be submitted because you'
                ' do not have permission to do so.')
            return

        questionnaire_object.status = 2
        questionnaire_object.save()

        messages.success(
            request, _('The questionnaire was successfully submitted.'))

    elif request.POST.get('publish'):

        # Previous status must be "pending"
        if questionnaire_object.status != 2:
            messages.error(
                request, 'The questionnaire could not be set public because '
                'it does not have to correct status.')
            return

        # Current user must be a moderator
        if not request.user.has_perm('questionnaire.can_moderate'):
            messages.error(
                request, 'The questionnaire could not be set public because '
                'you do not have permission to do so.')
            return

        questionnaire_object.status = 3
        questionnaire_object.save()

        added, errors = put_questionnaire_data(
            configuration_code, [questionnaire_object])

        # It is important to also put the data of the linked
        # questionnaires so changes (eg. name change) appear in their
        # links.
        links_by_configuration = {}
        for link in questionnaire_object.links.all():
            configuration_object = link.configurations.first()
            if configuration_object is None:
                continue
            if configuration_object.code not in links_by_configuration:
                links_by_configuration[configuration_object.code] = []
            links_by_configuration[configuration_object.code].append(link)

        for link_configuration, links in links_by_configuration.items():
            added, errors = put_questionnaire_data(link_configuration, links)

        messages.success(
            request, _('The questionnaire was successfully set public.'))
