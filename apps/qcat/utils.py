import urllib
from datetime import datetime


def find_dict_in_list(list_, key, value, not_found={}):
    """
    A helper function to find a dict based on a given key and value pair
    inside a list of dicts. Only the first occurence is returned if
    there are multiple dicts with the key and value.

    Args:
        ``list_`` (list): A list of dicts to search in.

        ``key`` (str): The key of the dict to look at.

        ``value`` (str): The value of the key the dict has to match.

    Kwargs:
        ``not_found`` (dict): The return value if no dict was found.
        Defaults to ``{}``.

    Returns:
        ``dict``. The dict if found. If not found, the return value as
        provided is returned or an empty dict by default.
    """
    if value is not None:
        for el in list_:
            if el.get(key) == value:
                return el
    return not_found


def is_empty_list_of_dicts(list_):
    """
    A helper function to find out if a list of dicts contains values or
    not. The following values are considered as empty values:

    * ``[{"key": ""}]``
    * ``[{"key": None}]``
    * ``[{"key": []}]``

    Args:
        ``list_`` (list): A list of dicts.

    Returns:
        ``bool``. ``True`` if the list contains only empty dicts,
        ``False`` if not.
    """
    for d in list_:
        for key, value in d.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if v is not None and v != '':
                        return False
            elif value is not None and value != '' and value != []:
                return False
    return True


def get_session_questionnaire(request, configuration_code, questionnaire_code):
    """
    Return the data for a questionnaire from the session. The
    questionnaire(s) are stored as a list in the session dictionary
    under the key ``questionnaires``.

    .. seealso::
        :func:`save_session_questionnaire` for the format of session
        data.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

        ``configuration_code`` (str): The code of the configuration of
        the questionnaire to retrieve.

        ``questionnaire_code`` (str): The code of the questionnaire to
        retrieve.

    Returns:
        ``dict``. The dictionary of the session data if found (with
        ``questionnaire`` and ``links``) or an empty dictionary (``{}``)
        if not found.
    """
    session_questionnaires = request.session.get('questionnaires', [])
    if not isinstance(session_questionnaires, list):
        return {}

    session_questionnaire = next((q for q in session_questionnaires if q.get(
        'configuration_code') == configuration_code and q.get(
        'questionnaire_code') == questionnaire_code), {})

    return session_questionnaire


def save_session_questionnaire(
        request, configuration_code, questionnaire_code,
        questionnaire_data=None, questionnaire_links=None,
        edited_questiongroups=None, old_questionnaire_data=None):
    """
    Save the data of a questionnaire to the session, using the key
    ``questionnaires``.

    The questionnaires are stored as a list in the session
    (``session['questionnaires']``) in the following format::

        [
            {
                "configuration_code": "CONFIGURATION_CODE",
                "questionnaire_code": "QUESTIONNAIRE_CODE",  # or "new"
                "modified": "DATETIME_OF_LAST_MODIFICATION",
                "questionnaire": {},  # data of the questionnaire
                "links": {},  # data of the links
            }
        ]

    Args:
        ``configuration_code`` (str): The code of the configuration of
        the questionnaire to store.

        ``questionnaire_code`` (str): The code of the questionnaire to
        store. If ``questionnaire_code`` is ``None``, the code is set to
        ``new``.

    Kwargs:
        ``questionnaire_data`` (dict): The data dictionary of the
        questionnaire to be stored.

        ``questionnaire_links`` (dict): The dictionary containing the
        links of the questionnaire. The format of the dictionary
        corresponds to the format used by the link forms to populate
        its fields.
    """
    session_questionnaires = request.session.get('questionnaires', [])
    if not isinstance(session_questionnaires, list):
        return

    session_questionnaire = {}
    for sq in session_questionnaires:
        if sq.get('configuration_code') == configuration_code and sq.get(
                'questionnaire_code') == questionnaire_code:
            session_questionnaire = sq
            if questionnaire_data is None:
                questionnaire_data = session_questionnaire.get(
                    'questionnaire', {})
            if questionnaire_links is None:
                questionnaire_links = session_questionnaire.get('links', {})
            if edited_questiongroups is None:
                edited_questiongroups = session_questionnaire.get(
                    'edited_questiongroups', [])
            if old_questionnaire_data is None:
                old_questionnaire_data = session_questionnaire.get(
                    'old_questionnaire', {})
            session_questionnaires.remove(sq)

    if questionnaire_data is None:
        questionnaire_data = {}
    if questionnaire_links is None:
        questionnaire_links = {}
    if edited_questiongroups is None:
        edited_questiongroups = []
    if old_questionnaire_data is None:
        old_questionnaire_data = {}

    session_questionnaire.update({
        'configuration_code': configuration_code,
        'questionnaire_code': questionnaire_code,
        'questionnaire': questionnaire_data,
        'old_questionnaire': old_questionnaire_data,
        'edited_questiongroups': edited_questiongroups,
        'links': questionnaire_links,
        'modified': str(datetime.now()),
    })

    session_questionnaires.append(session_questionnaire)

    request.session['questionnaires'] = session_questionnaires


def clear_session_questionnaire(
        request, configuration_code, questionnaire_code):
    """
    Clear the data of a questionnaire from the session key
    ``questionnaires``.

    Kwargs:
        ``configuration_code`` (str): The code of the configuration of
        the questionnaire to clear.

        ``questionnaire_code`` (str): The code of the questionnaire to
        clear.
    """
    session_questionnaires = request.session.get('questionnaires', [])
    if not isinstance(session_questionnaires, list):
        return

    for sq in session_questionnaires:
        if sq.get('configuration_code') == configuration_code and sq.get(
                'questionnaire_code') == questionnaire_code:
            session_questionnaires.remove(sq)

    request.session['questionnaires'] = session_questionnaires


def url_with_querystring(path, **kwargs):
    """
    Build a URL with query strings.

    Args:
        ``path`` (str): The base path of the URL before the query
        strings.

    Kwargs:
        ``**(key=value)``: One or more parameters as keys and values to
        be added as query strings.

    Returns:
        ``str``. A URL with query strings.
    """
    return path + '?' + urllib.parse.urlencode(kwargs)
