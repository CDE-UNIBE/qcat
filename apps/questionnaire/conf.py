from django.conf import settings  # noqa
from appconf import AppConf


class QuestionnaireConf(AppConf):
    """
    Verbose names for statuses and roles
    """
    # Status list
    DRAFT = 1
    SUBMITTED = 2
    REVIEWED = 3
    PUBLIC = 4
    REJECTED = 5
    INACTIVE = 6
    # Roles
    COMPILER = 'compiler'
    EDITOR = 'editor'
    REVIEWER = 'reviewer'
    PUBLISHER = 'publisher'
    SECRETARIAT = 'secretariat'
    LANDUSER = 'landuser'
    RESOURCEPERSON = 'resourceperson'
    FLAGGER = 'flagger'

    FLAG_UNCCD = 'unccd_bp'

    METADATA_KEYS = [
        'created',
        'updated',
        'compilers',
        'editors',
        'code',
        'configurations',
        'translations',
        'status',
        'flags',
        'original_locale',
    ]

    # A list of questiongroups which can be filtered for every configuration.
    # Those configurations that do not have these questiongroups will receive a
    # mapping for them anyways (to prevent ES crashes).
    GLOBAL_QUESTIONGROUPS = [
        'qg_name',
        'qg_location',
        'qg_funding_project',
        'qg_funding_institution',
    ]

    # Mapping for consistent field names on the API. See
    # questionnaire.api.views.QuestionnaireAPIMixin for usage.
    API_CHANGE_KEYS = {
        'app_definition': 'definition',
        'tech_definition': 'definition',
        'unccd_description': 'definition',
    }

    LOCK_TIME = 10  # Number of minutes that questionnaires are locked.
