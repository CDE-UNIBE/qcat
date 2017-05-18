from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import reindex, bulk

from configuration.models import Configuration
from configuration.utils import ConfigurationList
from questionnaire.models import Questionnaire
from questionnaire.serializers import QuestionnaireSerializer
from .utils import (
    get_analyzer,
    get_alias,
    force_strings)


def get_elasticsearch():
    """
    Return an instance of the elastic search with the connection as
    specified in the settings (``ES_HOST`` and ``ES_PORT``).

    Returns:
        ``elasticsearch.Elasticsearch``.
    """
    return Elasticsearch(
        [{'host': settings.ES_HOST, 'port': settings.ES_PORT}])

es = get_elasticsearch()


def get_mappings(questionnaire_configuration):
    """
    Return the mappings of the questiongroups of a Questionnaire. This
    is used to identify the types of fields, making it possible to query
    them properly.

    String values are objects themselves with a key for each language
    available.

    Args:
        ``questionnaire_configuration`` (
        :class:`configuration.configuration.QuestionnaireConfiguration`)

    Returns:
        ``dict``. A dict containing the mappings of a questionnaire
        fields.
    """
    language_codes = [l[0] for l in settings.LANGUAGES]

    data_properties = {}
    for questiongroup in questionnaire_configuration.get_questiongroups():
        qg_properties = {}
        for question in questiongroup.questions:
            if question.field_type in ['char', 'text']:
                q_properties = {}
                for language_code in language_codes:
                    q = {
                        'type': 'string',
                    }
                    analyzer = get_analyzer(language_code)
                    if analyzer:
                        q.update({
                            'analyzer': analyzer,
                        })
                    q_properties[language_code] = q
                qg_properties[question.keyword] = {
                    'properties': q_properties,
                }
            elif question.field_type in ['checkbox']:
                qg_properties[question.keyword] = {'type': 'string'}

        data_properties[questiongroup.keyword] = {
            'type': 'nested',
            'properties': qg_properties,
        }

    name_properties = {}
    for language_code in language_codes:
        q = {'type': 'string'}
        analyzer = get_analyzer(language_code)
        if analyzer:
            q.update({'analyzer': analyzer})
            name_properties[language_code] = q

    multilanguage_string_properties = {}
    for language_code in language_codes:
        multilanguage_string_properties[language_code] = {
            'type': 'string'
        }
    link_structure = {
        'code': {
            'type': 'string',
        },
        'configuration': {
            'type': 'string',
        },
        'name': {
            'properties': multilanguage_string_properties,
        },
        'url': {
            'properties': multilanguage_string_properties,
        }
    }

    # Add the global questiongroups to the mapping if they are not already part
    # of it. This is needed to prevent crashes when filtering (nested) by these
    # questiongroups in configurations that do not have these questiongroups
    # (e.g. UNCCD configuration).
    for global_questiongroup in settings.QUESTIONNAIRE_GLOBAL_QUESTIONGROUPS:
        if global_questiongroup not in data_properties.keys():
            data_properties[global_questiongroup] = {
                'type': 'nested',
                'properties': {},
            }

    mappings = {
        'questionnaire': {
            'properties': {
                'data': {
                    'properties': data_properties,
                },
                'created': {
                    'type': 'date'
                },
                'updated': {
                    'type': 'date'
                },
                'translations': {
                    'type': 'string'
                },
                'configurations': {
                    'type': 'string'
                },
                'code': {
                    'type': 'string'
                },
                'name': {
                    'properties': name_properties
                },
                'compilers': {
                    'type': 'nested',
                    'properties': {
                        'id': {
                            'type': 'integer',
                        },
                        'name': {
                            'type': 'string',
                        },
                    }
                },
                'editors': {
                    'type': 'nested',
                    'properties': {
                        'id': {
                            'type': 'integer',
                        },
                        'name': {
                            'type': 'string',
                        },
                    }
                },
                'links': {
                    'type': 'nested',
                    'properties': link_structure,
                },
                'flags': {
                    'type': 'nested',
                    'properties': {
                        'flag': {
                            'type': 'string',
                        },
                        'name': {
                            'type': 'string',
                        },
                    }
                },
                # 'list_data' is added dynamically
            }
        }
    }

    return mappings


def create_or_update_index(configuration_code, mappings):
    """
    Create or update an index for a configuration.

    New indices are created with an alias pointing to it. The alias is
    composed of the prefix as specified in the settings
    (``ES_INDEX_PREFIX``) followed by the ``configuration_code`` as
    provided.

    .. seealso::
        :func:`search.utils.get_alias`

    Updates of indices happen by creating a new index, replacing link of
    the alias and deleting the old index.

    .. seealso::
        https://www.elastic.co/blog/changing-mapping-with-zero-downtime

    Args:
        ``configuration_code`` (str): The code of the configuration.

        ``mappings`` (dict): A dictionary containing the mapping of the
        fields of the Questionnaire.

        .. seealso::
            :func:`get_mappings`

    Returns:
        ``bool``. A boolean indicating whether the creation/update of
        the index was successful or not.

        ``list``. A list of strings containing the logs of the actions
        performed.

        ``str``. An optional error message.
    """
    logs = []
    body = {
        'mappings': mappings,
        'settings': {
            'index': {
                'mapping': {
                    'nested_fields': {
                        'limit': settings.ES_NESTED_FIELDS_LIMIT
                    }
                }
            }
        }
    }

    # Check if there is already an alias pointing to the index.
    alias = get_alias([configuration_code])
    alias_exists = es.indices.exists_alias(name=alias)

    if alias_exists is not True:
        # If there is no alias yet, create an index and an alias
        # pointing to it.
        logs.append(
            'Alias "{}" does not exist, an index is being created'.format(
                alias))
        index = '{}_1'.format(alias)
        index_created = es.indices.create(index=index, body=body)
        if index_created.get('acknowledged') is not True:
            return False, logs, 'Index could not be created: {}'.format(
                index_created)
        logs.append('Index "{}" was created'.format(index))
        alias_created = es.indices.put_alias(index=index, name=alias)
        if alias_created.get('acknowledged') is not True:
            return False, logs, 'Alias could not be created: {}'.format(
                alias_created)
        logs.append('Alias "{}" was created'.format(alias))
    else:
        logs.append('Alias "{}" found'.format(alias))
        old_index, new_index = get_current_and_next_index(alias)
        index_created = es.indices.create(index=new_index, body=body)
        if index_created.get('acknowledged') is not True:
            return (False, logs,
                    'Updated Index could not be created: "{}"'.format(
                        index_created))
        logs.append('Index "{}" was created'.format(new_index))
        data_transfer, data_error = reindex(es, old_index, new_index)
        logs.append('Data transferred: "{}", data error: "{}"'.format(
            data_transfer, data_error))
        es.indices.refresh(index=new_index)
        logs.append('Index "{}" was refreshed'.format(new_index))
        alias_created = es.indices.put_alias(index=new_index, name=alias)
        if alias_created.get('acknowledged') is not True:
            return (
                False, logs, 'Updated Alias could not be created: {}'.format(
                    alias_created))
        logs.append('Alias to "{}" was created'.format(new_index))
        alias_deleted = es.indices.delete_alias(index=old_index, name=alias)
        if alias_deleted.get('acknowledged') is not True:
            return False, logs, 'Old Alias could not be deleted: {}'.format(
                alias_deleted)
        logs.append('Alias to "{}" was deleted'.format(old_index))
        index_deleted = es.indices.delete(index=old_index)
        if index_deleted.get('acknowledged') is not True:
            return False, logs, 'Old Index could not be deleted: {}'.format(
                index_deleted)
        logs.append('Index "{}" was deleted'.format(old_index))

    return True, logs, ''


def put_questionnaire_data(configuration_code, questionnaire_objects, **kwargs):
    """
    Add a list of documents to the index. New documents will be created,
    existing documents will be updated.

    Args:
        ``configuration_code`` (str): The code of the Questionnaire
        configuration corresponding to the data.

        ``questionnaire_objects`` (list): A list (queryset) of
        :class:`questionnaire.models.Questionnaire` objects.

    Returns:
        ``int``. Count of objects created or updated.

        ``list``. A list of errors occurred.
    """
    config_list = ConfigurationList()
    questionnaire_configuration = config_list.get(configuration_code)
    alias = get_alias([configuration_code])

    actions = []
    for obj in questionnaire_objects:
        serialized = QuestionnaireSerializer(
            obj, config=questionnaire_configuration
        ).data

        # The serializer calls a method (get_list_data) on the configuration
        # object, which returns values that are prepared to be presented on the
        # frontend and include lazy translation objects. Cast them to strings.
        serialized['list_data'] = force_strings(serialized['list_data'])
        action = {
            '_index': alias,
            '_type': 'questionnaire',
            '_id': obj.id,
            '_source': serialized,
        }
        actions.append(action)

    actions_executed, errors = bulk(es, actions, **kwargs)

    es.indices.refresh(index=alias)
    return actions_executed, errors


def put_all_data():
    """
    Put data from all configurations to the es index.
    """
    configurations = Configuration.objects.filter(active=True)
    for configuration in configurations:
        questionnaires = Questionnaire.with_status.public().filter(
            configurations=configuration
        )
        if questionnaires.exists():
            put_questionnaire_data(
                configuration_code=configuration.code,
                questionnaire_objects=questionnaires,
                request_timeout=60
            )


def delete_questionnaires_from_es(configuration_code, questionnaire_objects):
    """
    Remove specific Questionnaires from the index.

    Args:
        ``configuration_code`` (str): The code of the Questionnaire
        configuration corresponding to the data.

        ``questionnaire_objects`` (list): A list (queryset) of
        :class:`questionnaire.models.Questionnaire` objects to be
        removed.
    """
    alias = get_alias([configuration_code])
    for questionnaire in questionnaire_objects:
        try:
            es.delete(
                index=alias, doc_type='questionnaire', id=questionnaire.id)
        except:
            pass


def delete_all_indices():
    """
    Delete all the indices starting with the prefix as specified in the
    settings (``ES_INDEX_PREFIX``).

    Returns:
        ``bool``. A boolean indicating whether the operation was carried
        out successfully or not.

        ``str``. An optional error message if the operation was not
        successful.
    """
    deleted = es.indices.delete(index='{}*'.format(settings.ES_INDEX_PREFIX))
    if deleted.get('acknowledged') is not True:
        return (False, 'Indices could not be deleted')

    return True, ''


def delete_single_index(index):
    """
    Delete a specific index.

    Args:
        ``ìndex`` (str): The name of the index to be deleted.

    Returns:
        ``bool``. A boolean indicating whether the operation was carried
        out successfully or not.

        ``str``. An optional error message if the operation was not
        successful.
    """
    deleted = es.indices.delete(
        index='{}{}'.format(settings.ES_INDEX_PREFIX, index), ignore=[404])
    if deleted.get('acknowledged') is not True:
        return (False, 'Index could not be deleted')

    return True, ''


def get_current_and_next_index(alias):
    """
    Get the current and next index of an alias. Both the currently
    linked index and the next index to be used (by increasing the
    suffix) are returned.

    Returns:
        ``str``. The name of the index currently linked by the alias.

        ``str``. The name of the next index to be used by the alias.
    """
    if es.indices.exists_alias(name=alias) is not True:
        return None, None
    aliased_index = es.indices.get_alias(name=alias)
    found_index = next(iter(aliased_index.keys()))
    found_version = found_index.split('{}_'.format(alias))
    try:
        found_version = int(found_version[1])
    except:
        found_version = 1
    next_index = '{}_{}'.format(alias, found_version + 1)
    return found_index, next_index
