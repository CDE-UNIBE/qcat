from importlib import import_module
from django.conf import settings
session_store = import_module(settings.SESSION_ENGINE).SessionStore()


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
        ``not_found`` (): The return value if no dict was found.
        Defaults to ``{}``.
    """
    if value is not None:
        for el in list_:
            if el.get(key) == value:
                return el
    return not_found


def get_session_questionnaire():
    """
    Return the data for a questionnaire from the session. The
    questionnaire(s) are stored in the session dictionary under the key
    ``session_questionnaires``.

    .. todo::
        Currently, only one questionnaire is stored to the session. In
        the fututre, it should be possible to store (and retrieve)
        multiple questionnaires.

    Returns:
        ``dict``. The data dictionary of the questionnaire as found in
        the session or an empty dictionary (``{}``) if not found.
    """
    session_questionnaires = session_store.get('session_questionnaires')
    if (isinstance(session_questionnaires, list)
            and len(session_questionnaires) > 0):
        # TODO: Do not always return first questionnaire
        return session_questionnaires[0]
    else:
        return {}


def save_session_questionnaire(session_questionnaire):
    """
    Save the data of a questionnaire to the session, using the key
    ``session_questionnaires``.

    .. todo::
        Currently, only one questionnaire is stored to the session. In
        the fututre, it should be possible to store (and retrieve)
        multiple questionnaires.

    Args:
        ``session_questionnaire`` (dict): The data dictionary of the
        questionnaire to be stored.
    """
    session_store['session_questionnaires'] = [session_questionnaire]
    session_store.save()


def clear_session_questionnaire():
    """
    Clear the data of a questionnaire from the session key
    ``session_questionnaires``.

    .. todo::
        Currently, only one questionnaire is stored to the session. In
        the fututre, it should be possible to store (and delete)
        multiple questionnaires.
    """
    session_store['session_questionnaires'] = []
    session_store.save()
