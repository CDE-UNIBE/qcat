# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.conf import settings  # noqa

from appconf import AppConf


class NotificationsConf(AppConf):
    CREATE = 1
    DELETE = 2
    CHANGE_STATUS = 3
    ADD_MEMBER = 4
    REMOVE_MEMBER = 5
    EDIT_CONTENT = 6
    FINISH_EDITING = 7

    ACTIONS = (
        (CREATE, _('created questionnaire')),
        (DELETE, _('deleted questionnaire')),
        (CHANGE_STATUS, _('changed status')),
        (ADD_MEMBER, _('invited member')),
        (REMOVE_MEMBER, _('removed member')),
        (EDIT_CONTENT, _('edited content')),
        (FINISH_EDITING, _('editor finished'))
    )

    ACTION_ICON = {
        CREATE: 'icon-plus',
        DELETE: 'icon-minus',
        'status-reject': 'icon-rewind',
        'status-approve': 'icon-forward',
        ADD_MEMBER: 'icon-member-add',
        REMOVE_MEMBER: 'icon-member-remove',
        EDIT_CONTENT: 'icon-pencil',
        FINISH_EDITING: 'icon-edit-approve',
    }

    # Mapping of user permissions and allowed questionnaire statuses
    QUESTIONNAIRE_STATUS_PERMISSIONS = {
        'questionnaire.submit_questionnaire': settings.QUESTIONNAIRE_DRAFT,
        'questionnaire.review_questionnaire': settings.QUESTIONNAIRE_SUBMITTED,
        'questionnaire.publish_questionnaire': settings.QUESTIONNAIRE_REVIEWED
    }
    QUESTIONNAIRE_MEMBERSHIP_PERMISSIONS = {
        settings.QUESTIONNAIRE_COMPILER: [settings.QUESTIONNAIRE_DRAFT],
        settings.QUESTIONNAIRE_EDITOR: [],
        settings.QUESTIONNAIRE_REVIEWER: [settings.QUESTIONNAIRE_SUBMITTED],
        settings.QUESTIONNAIRE_PUBLISHER: [settings.QUESTIONNAIRE_REVIEWED],
        settings.QUESTIONNAIRE_SECRETARIAT: [settings.QUESTIONNAIRE_SUBMITTED, settings.QUESTIONNAIRE_REVIEWED],
        settings.ACCOUNTS_UNCCD_ROLE_NAME: [],
        settings.QUESTIONNAIRE_LANDUSER: [],
        settings.QUESTIONNAIRE_RESOURCEPERSON: []
    }
    # Verbs are only available in past tense ('submitted', 'reviewed', ...), but
    # present is required for selected statuses.
    QUESTIONNAIRE_NEXT_STATUS_TEXT = {
        settings.QUESTIONNAIRE_SUBMITTED: _('review'),
        settings.QUESTIONNAIRE_REVIEWED: _('publication'),
    }

    # All actions that should be listed on 'my slm data' -> notifications.
    # Some actions are depending on the role (i.e. compilers see all edits).
    USER_PROFILE_ACTIONS = [
        CREATE, DELETE, CHANGE_STATUS, ADD_MEMBER, REMOVE_MEMBER
    ]

    # All actions that should trigger an email
    EMAIL_ACTIONS = [CHANGE_STATUS]

    TEASER_PAGINATE_BY = 5
    LIST_PAGINATE_BY = 10
