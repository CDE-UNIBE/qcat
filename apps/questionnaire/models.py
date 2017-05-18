import contextlib
import json
import collections

import os
import requests
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import GeometryCollection, GEOSGeometry
from os.path import join
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.contrib.messages import WARNING, SUCCESS
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _, get_language, activate
from django.utils import timezone
from django_pgjson.fields import JsonBField
from staticmap import StaticMap, CircleMarker, Polygon

from accounts.models import User
from configuration.cache import get_configuration
from configuration.models import Configuration, Value
from qcat.errors import ConfigurationError
from .signals import change_status, create_questionnaire

from .conf import settings
from .errors import QuestionnaireLockedException
from .querysets import StatusQuerySet, LockStatusQuerySet

from questionnaire.upload import (
    create_thumbnails,
    get_url_by_file_name,
    get_file_path,
    store_file,
    get_upload_folder_structure, get_upload_folder_path)

STATUSES = (
    (settings.QUESTIONNAIRE_DRAFT, _('Draft')),
    (settings.QUESTIONNAIRE_SUBMITTED, _('Submitted')),
    (settings.QUESTIONNAIRE_REVIEWED, _('Reviewed')),
    (settings.QUESTIONNAIRE_PUBLIC, _('Public')),
    (settings.QUESTIONNAIRE_REJECTED, _('Rejected')),
    (settings.QUESTIONNAIRE_INACTIVE, _('Inactive')),
)
STATUSES_CODES = (
    (settings.QUESTIONNAIRE_DRAFT, 'draft'),
    (settings.QUESTIONNAIRE_SUBMITTED, 'submitted'),
    (settings.QUESTIONNAIRE_REVIEWED, 'reviewed'),
    (settings.QUESTIONNAIRE_PUBLIC, 'public'),
    (settings.QUESTIONNAIRE_REJECTED, 'rejected'),
    (settings.QUESTIONNAIRE_INACTIVE, 'inactive'),
)

QUESTIONNAIRE_ROLES = (
    # Functional roles
    (settings.QUESTIONNAIRE_COMPILER, _('Compiler')),
    (settings.QUESTIONNAIRE_EDITOR, _('Editor')),
    (settings.QUESTIONNAIRE_REVIEWER, _('Reviewer')),
    (settings.QUESTIONNAIRE_PUBLISHER, _('Publisher')),
    (settings.QUESTIONNAIRE_SECRETARIAT, _('WOCAT Secretariat')),
    (settings.ACCOUNTS_UNCCD_ROLE_NAME, _('UNCCD Focal Point')),
    # Content roles only, no privileges attached
    (settings.QUESTIONNAIRE_LANDUSER, _('Land User')),
    (settings.QUESTIONNAIRE_RESOURCEPERSON, _('Key resource person')),
)

QUESTIONNAIRE_FLAGS = (
    (settings.QUESTIONNAIRE_FLAG_UNCCD, _('UNCCD Best Practice')),
)

QUESTIONNAIRE_FLAGS_HELPTEXT = (
    (settings.QUESTIONNAIRE_FLAG_UNCCD, _(
        'Submitted as SLM best practice to UNCCD by the national focal point')),
)


class Questionnaire(models.Model):
    """
    The model representing a Questionnaire instance. This is the common
    denominator for all version (:class:`QuestionnaireVersion`) of a
    Questionnaire.
    """
    data = JsonBField()
    created = models.DateTimeField()
    updated = models.DateTimeField()
    uuid = models.CharField(max_length=64, default=uuid4)
    code = models.CharField(max_length=64, default='')
    geom = models.GeometryField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUSES)
    version = models.IntegerField()
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through='QuestionnaireMembership')
    configurations = models.ManyToManyField(
        'configuration.Configuration', through='QuestionnaireConfiguration')
    links = models.ManyToManyField(
        'self', through='QuestionnaireLink', symmetrical=False,
        related_name='linked_to+')
    flags = models.ManyToManyField('Flag')

    objects = models.Manager()
    with_status = StatusQuerySet.as_manager()

    class Meta:
        ordering = ['-updated']
        permissions = (
            ("review_questionnaire", "Can review questionnaire"),
            ("publish_questionnaire", "Can publish questionnaire"),
            ("assign_questionnaire",
             "Can assign questionnaire (for review/publish)"),
            ("view_questionnaire", "Can view questionnaire"),
            ("edit_questionnaire", "Can edit questionnaire"),
            ("change_compiler", "Can change compiler of questionnaire"),
            ("flag_unccd_questionnaire", "Can flag UNCCD questionnaire"),
            ("unflag_unccd_questionnaire", "Can unflag UNCCD questionnaire"),
        )
        unique_together = (('code', 'version'),)

    def _get_url_from_configured_app(self, url_name: str) -> str:
        """
        Try to resolve the proper code for the object, using it as namespace.

        If some day, the configurations code is not the exact same string as
        the application name, a 'mapping' dict is required.
        """
        conf = self.configurations.filter(
            active=True
        ).exclude(
            code=''
        ).only(
            'code'
        )
        if conf.exists() and conf.count() == 1:
            with contextlib.suppress(NoReverseMatch):
                return reverse('{app_name}:{url_name}'.format(
                    app_name=conf.first().code,
                    url_name=url_name
                ), kwargs={'identifier': self.code})
        return None

    def get_absolute_url(self):
        """
        Detail view url of the questionnaire. Important: don't use type hints
        as djangorestframework as of now throws errors
        (https://github.com/tomchristie/django-rest-framework/pull/4076)
        """
        return self._get_url_from_configured_app('questionnaire_details')

    def get_edit_url(self) -> str:
        """
        Edit view url of the questionnaire
        """
        return self._get_url_from_configured_app('questionnaire_edit')

    def update_data(self, data, updated, configuration_code):
        """
        Helper function to just update the data of the questionnaire
        without creating a new instance.

        Args:
            ``data`` (dict): The data dictionary

            ``updated`` (timestamp): The timestamp of the update

            ``configuration_code`` (str): The configuration code.

        Returns:
            ``Questionnaire``
        """
        self.data = data
        self.updated = updated
        self.save()
        # Unblock all questionnaires with this code, as all questionnaires with
        # this code are blocked for editing.
        Lock.objects.filter(
            questionnaire_code=self.code
        ).update(
            is_finished=True
        )

        try:
            self.update_geometry(configuration_code=configuration_code)
        except:
            pass

        # Update the users attached to the questionnaire
        self.update_users_from_data(configuration_code)

        return self

    @staticmethod
    def create_new(
            configuration_code, data, user, previous_version=None, status=1,
            created=None, updated=None, old_data=None, languages=None):
        """
        Create and return a new Questionnaire.

        Args:
            ``configuration_code`` (str): The code of the configuration.
            An active configuration with the given code needs to exist.
            The configuration is linked to the questionnaire.

            ``data`` (dict): The questionnaire data.

        Kwargs:
            ``previous_version`` (questionnaire.models.Questionnaire):
            The previous version of the questionnaire.

            ``status`` (int): The status of the questionnaire to be
            created. Defaults to 1 (draft) if not set.

            ``created`` (datetime): A specific datetime object to be set
            as created timestamp. Defaults to ``now`` if not set.

            ``updated`` (datetime): A specific datetime object to be set
            as updated timestamp. Defaults to ``now`` if not set.

            ``old_data`` (dict): The data dictionary containing the old data of
            the questionnaire.

            ``languages`` (list): An optional list of languages in which a newly
            created questionnaire is available. Should only be used when
            importing data.

        Returns:
            ``questionnaire.models.Questionnaire``. The created
            Questionnaire.

        Raises:
            ``ValidationError``
        """
        if updated is None:
            updated = timezone.now()
        if created is None:
            created = timezone.now()

        if previous_version:
            created = previous_version.created
            roles, permissions = previous_version.get_roles_permissions(user)
            code = previous_version.code
            version = previous_version.version
            uuid = previous_version.uuid

            # Unblock all other questionnaires with same code
            Lock.objects.filter(
                questionnaire_code=code
            ).update(
                is_finished=True
            )

            if 'edit_questionnaire' not in permissions:
                raise ValidationError(
                    'You do not have permission to edit the questionnaire.')

            if previous_version.status == settings.QUESTIONNAIRE_PUBLIC:
                # Edit of a public questionnaire: Create new version
                # with the same code
                version = previous_version.version + 1
                languages = previous_version.translations

            elif previous_version.status == settings.QUESTIONNAIRE_DRAFT:
                # Edit of a draft questionnaire: Only update the data
                previous_version.update_data(data, updated, configuration_code)
                previous_version.add_translation_language(original=False)
                return previous_version

            elif previous_version.status == settings.QUESTIONNAIRE_SUBMITTED:
                # Edit of a submitted questionnaire: Only update the data
                # User must be reviewer!
                if 'review_questionnaire' not in permissions:
                    raise ValidationError(
                        'You do not have permission to edit the '
                        'questionnaire.')
                previous_version.update_data(data, updated, configuration_code)
                previous_version.add_translation_language(original=False)
                return previous_version

            elif previous_version.status == settings.QUESTIONNAIRE_REVIEWED:
                # Edit of a reviewed questionnaire: Only update the data
                # User must be publisher!
                if 'publish_questionnaire' not in permissions:
                    raise ValidationError(
                        'You do not have permission to edit the '
                        'questionnaire.')
                previous_version.update_data(data, updated, configuration_code)
                previous_version.add_translation_language(original=False)
                return previous_version

            else:
                raise ValidationError(
                    'The questionnaire cannot be updated because of its status'
                    ' "{}"'.format(previous_version.status))
        else:
            code = ''  # Will be generated later
            version = 1
            uuid = uuid4()
        if status not in [s[0] for s in STATUSES]:
            raise ValidationError('"{}" is not a valid status'.format(status))
        configuration = Configuration.get_active_by_code(configuration_code)
        if configuration is None:
            raise ValidationError(
                'No active configuration found for code "{}"'.format(
                    configuration_code))
        questionnaire = Questionnaire.objects.create(
            data=data, uuid=uuid, code=code, version=version, status=status,
            created=created, updated=updated)

        if not previous_version:
            # Generate and set a new code for the questionnaire
            from configuration.utils import create_new_code
            code = create_new_code(questionnaire, configuration_code)
            questionnaire.code = code

        create_questionnaire.send(
            sender=settings.NOTIFICATIONS_CREATE,
            questionnaire=questionnaire,
            user=user
        )

        questionnaire.update_geometry(configuration_code=configuration_code)

        # TODO: Not all configurations should be the original ones!
        QuestionnaireConfiguration.objects.create(
            questionnaire=questionnaire, configuration=configuration,
            original_configuration=True)

        if not languages:
            questionnaire.add_translation_language(original=True)
        else:
            for i, language in enumerate(languages):
                original = i == 0
                questionnaire.add_translation_language(
                    original=original, language=language)

        if previous_version:
            # Copy all the functional user roles from the old version
            user_roles = [settings.QUESTIONNAIRE_COMPILER,
                          settings.QUESTIONNAIRE_EDITOR,
                          settings.QUESTIONNAIRE_REVIEWER,
                          settings.QUESTIONNAIRE_PUBLISHER]
            for role in user_roles:
                for old_user in previous_version.get_users_by_role(role):
                    questionnaire.add_user(old_user, role)

            # Also copy any flags
            questionnaire.flags.add(*previous_version.flags.all())
        else:
            questionnaire.add_user(user, settings.QUESTIONNAIRE_COMPILER)
        questionnaire.update_users_from_data(
            configuration_code)

        return questionnaire

    def add_translation_language(self, original=False, language=None):
        """
        Add a language as a translation of the questionnaire. Add it only once.

        Args:
            original: bool. Whether the language is the original language or not

            language: string. Manually set the language of the translation. If
            not provided, it is looked up using get_language().

        Returns:

        """
        if language is None:
            language = get_language()
        if language not in self.translations:
            QuestionnaireTranslation.objects.create(
                questionnaire=self, language=language,
                original_language=original)
            # Delete cached translation property
            try:
                delattr(self, 'translations')
            except AttributeError:
                pass

    def get_id(self):
        return self.id

    def get_roles_permissions(self, current_user):
        """
        Return the roles and permissions of a given user for the current
        questionnaire.

        The following rules apply:
            * Compilers and editors can edit questionnaires if the status is
              either draft or public.
            * Compilers can submit and assign questionnaires if the status is
              draft.
            * Reviewers can edit and review questionnaires if the status is
              submitted.
            * Publishers can edit and review questionnaires if the status is
              reviewed.
            * Secretariat members can assign questionnaires if the status is
              submitted (assign reviewers) or published (assign publishers).

        Permissions to be returned are:
            * ``edit_questionnaire``
            * ``submit_questionnaire``
            * ``review_questionnaire``
            * ``publish_questionnaire``
            * ``assign_questionnaire``

        Args:
            ``current_user`` (User): The user.

        Returns:
            ``namedtuple``. A named tuple with
                - roles: A list of roles of the user for this questionnaire
                  object as tuple (role_code, role_name)
                - permissions. A list of permissions of the user for this
                  questionnaire object.
        """
        roles = []
        permissions = []

        RolesPermissions = collections.namedtuple(
            'RolesPermissions', ['roles', 'permissions'])

        if not isinstance(current_user, get_user_model()):
            return RolesPermissions(roles=roles, permissions=permissions)

        # Permissions based on role of current user in questionnaire
        permission_groups = {
            settings.QUESTIONNAIRE_COMPILER: [{
                'status': [settings.QUESTIONNAIRE_DRAFT,
                           settings.QUESTIONNAIRE_PUBLIC],
                'permissions': ['edit_questionnaire', 'delete_questionnaire']
            }, {
                'status': [settings.QUESTIONNAIRE_DRAFT],
                'permissions': ['submit_questionnaire', 'assign_questionnaire']
            }],
            settings.QUESTIONNAIRE_EDITOR: [{
                'status': [settings.QUESTIONNAIRE_DRAFT,
                           settings.QUESTIONNAIRE_PUBLIC],
                'permissions': ['edit_questionnaire']
            }],
            settings.QUESTIONNAIRE_REVIEWER: [{
                'status': [settings.QUESTIONNAIRE_SUBMITTED],
                'permissions': ['edit_questionnaire', 'review_questionnaire']
            }],
            settings.QUESTIONNAIRE_PUBLISHER: [{
                'status': [settings.QUESTIONNAIRE_REVIEWED],
                'permissions': ['edit_questionnaire', 'publish_questionnaire']
            }]
        }
        for member_role, user in self.get_users(user=current_user):
            permission_group = permission_groups.get(member_role)
            if not permission_group:
                continue

            add_role = False
            for access_level in permission_group:
                if self.status in access_level['status']:
                    permissions.extend(access_level['permissions'])
                    add_role = True

            if add_role is True:
                roles.append((member_role, dict(QUESTIONNAIRE_ROLES).get(member_role)))

        # General permissions of user
        user_permissions = current_user.get_all_permissions()
        if ('questionnaire.review_questionnaire' in user_permissions
                and self.status in [settings.QUESTIONNAIRE_SUBMITTED]):
            permissions.extend(['review_questionnaire', 'edit_questionnaire'])
            role = settings.QUESTIONNAIRE_REVIEWER
            roles.append(
                (role, dict(QUESTIONNAIRE_ROLES).get(role)))
        if ('questionnaire.publish_questionnaire' in user_permissions
                and self.status in [settings.QUESTIONNAIRE_REVIEWED]):
            permissions.extend(['publish_questionnaire', 'edit_questionnaire'])
            role = settings.QUESTIONNAIRE_PUBLISHER
            roles.append(
                (role, dict(QUESTIONNAIRE_ROLES).get(role)))
        if 'questionnaire.assign_questionnaire' in user_permissions:
            # Piggybacking on the "assign_questionnaire" permission to identify
            # WOCAT secretariat users as this permission is only available for
            # this role.
            permissions.extend(
                ['edit_questionnaire', 'delete_questionnaire',
                 'submit_questionnaire', 'review_questionnaire',
                 'publish_questionnaire', 'change_compiler'])
            if self.status in [settings.QUESTIONNAIRE_SUBMITTED,
                               settings.QUESTIONNAIRE_REVIEWED]:
                permissions.extend(['assign_questionnaire'])
            role = settings.QUESTIONNAIRE_SECRETARIAT
            roles.append(
                (role, dict(QUESTIONNAIRE_ROLES).get(role)))

        # UNCCD Flagging
        questionnaire_country = self.get_question_data('qg_location', 'country')
        if len(questionnaire_country) == 1 \
                and self.status in [settings.QUESTIONNAIRE_PUBLIC]:
            for country in current_user.get_unccd_countries():
                if country.keyword == questionnaire_country[0]:

                    role = settings.ACCOUNTS_UNCCD_ROLE_NAME
                    roles.append(
                        (role, dict(QUESTIONNAIRE_ROLES).get(role)))

                    try:
                        self.flags.get(flag=settings.QUESTIONNAIRE_FLAG_UNCCD)
                        # Flag already exists
                        permissions.extend(['unflag_unccd_questionnaire'])
                    except Flag.DoesNotExist:
                        # No flag yet
                        permissions.extend(['flag_unccd_questionnaire'])

        # Remove duplicates
        permissions = list(set(permissions))
        roles = list(set(roles))

        # Do the translation of the role names
        translated_roles = []
        for role_keyword, role_name in roles:
            translated_roles.append((role_keyword, _(role_name)))

        return RolesPermissions(roles=translated_roles, permissions=permissions)

    def get_question_data(self, qg_keyword, q_keyword):
        """
        Get the raw question data by keyword. This does not translate the values
        or return the labelled choices. For this, use
        QuestionnaireConfiguration.

        Args:
            qg_keyword: (str): The keyword of the questiongroup.
            q_keyword: (str): The keyword of the question.

        Returns:
            (list). A list of (raw) values.
        """
        data = []
        if self.data:
            for q_data in self.data.get(qg_keyword, []):
                for key, value in q_data.items():
                    if key == q_keyword:
                        data.append(value)
        return data

    def get_name(self, locale='') -> str:
        """
        Return the name of the questionnaire, based on the configuration.
        """
        active_config = self.configurations.filter(
            active=True
        ).first()
        if not active_config:
            raise ConfigurationError(
                'No active configuration for questionnaire {}'.format(self.id)
            )
        config = get_configuration(active_config.code)
        names = config.get_questionnaire_name(self.data) or {}
        name = names.get(locale or get_language())
        if name:
            # omit additional query
            return name

        original_lang = self.questionnairetranslation_set.filter(
            original_language=True
        ).first()
        if original_lang and names.get(original_lang.language):
            return names[original_lang.language]

        return ''

    def get_countries(self) -> []:
        """
        Return list of translated country names.
        """
        codes = self.get_question_data('qg_location', 'country')
        if codes:
            values = Value.objects.filter(keyword__in=codes)
            if values.exists():
                return [value.get_translation(keyword='label') for value in values]
        return []

    def update_geometry(self, configuration_code, force_update=False):
        """
        Update the geometry of a questionnaire based on the GeoJSON found in the
        data json.

        Args:
            configuration_code:

        Returns:
            -
        """
        def get_geometry_from_string(geometry_string):
            """
            Extract and convert the geometry from a (GeoJSON) string.

            Args:
                geometry_string: The geometry as (GeoJSON) string.

            Returns:
                A GeometryCollection or None.
            """

            if geometry_string is None:
                return None

            try:
                geometry_json = json.loads(geometry_string)
            except json.decoder.JSONDecodeError:
                return None
            geoms = []
            for feature in geometry_json.get('features', []):
                try:
                    feature_geom = GEOSGeometry(
                        json.dumps(feature.get('geometry')))
                except ValueError:
                    continue
                except GDALException:
                    continue
                geoms.append(feature_geom)

            if geoms:
                return GeometryCollection(tuple(geoms))

            else:
                return None

        conf_object = get_configuration(configuration_code)
        geometry_value = conf_object.get_questionnaire_geometry(self.data)
        geometry = get_geometry_from_string(geometry_value)

        geometry_changed = self.geom != geometry

        try:
            self.geom = geometry
            self.save()
        except ValidationError:
            return

        if self.geom is None or (not force_update and not geometry_changed):
            # If there is no geometry or if it did not change, there is no need
            # to create the static map image (again)
            return

        # Create static map
        width = 1000
        height = 800
        marker_diameter = 24
        marker_color = '#0036FF'

        m = StaticMap(width, height)

        for point in iter(self.geom):
            m.add_marker(CircleMarker((point.x,  point.y), marker_color, marker_diameter))

        bbox = None
        questionnaire_country = self.get_question_data('qg_location', 'country')

        if len(questionnaire_country) == 1:
            country_iso3 = questionnaire_country[0].replace('country_', '')
            country_iso2 = settings.CONFIGURATION_COUNTRY_ISO_MAPPING.get(
                country_iso3)

            if country_iso2:
                r = requests.get(
                    'http://api.geonames.org/countryInfoJSON?username=wocat_webdev&country={}'.format(
                        country_iso2))
                geonames_country = r.json().get('geonames')

                if len(geonames_country) == 1:
                    ctry = geonames_country[0]
                    poly_coords = [
                        [ctry.get('west'), ctry.get('north')],
                        [ctry.get('west'), ctry.get('south')],
                        [ctry.get('east'), ctry.get('south')],
                        [ctry.get('east'), ctry.get('north')],
                        [ctry.get('west'), ctry.get('north')]
                    ]

                    bbox = Polygon(poly_coords, None, None)

        if bbox:
            m.add_polygon(bbox)
            image = m.render()
        else:
            # No bbox found, guess zoom level
            image = m.render(zoom=6)

        map_folder = get_upload_folder_path(str(self.uuid), subfolder='maps')
        if not os.path.exists(map_folder):
            os.makedirs(map_folder)

        filename = '{}_{}.jpg'.format(self.uuid, self.version)
        image.save(os.path.join(map_folder, filename))

    def add_flag(self, flag):
        """
        Add a Flag object to the questionnaire. Add it only once.

        Args:
            flag: (Flag): The flag to be added.
        """
        if flag not in self.flags.all():
            self.flags.add(flag)

    def get_user(self, user, role):
        """
        Get and return a user of the Questionnaire by role.

        Args:
            user: (User) The user.
            role: (str): The role of the user.

        Returns:
            User or None.
        """
        membership = self.questionnairemembership_set.filter(
            user=user, role=role).first()
        if membership:
            return membership.user
        return None

    def get_users(self, **kwargs):
        """
        Helper function to return the users of a questionnaire along
        with their role in this membership.

        Returns:
            ``list``. A list of tuples where each entry contains the
            following elements:

            - [0]: ``string``. The role of the membership.

            - [1]: ``accounts.models.User``. The user object.
        """
        users = []
        for membership in self.questionnairemembership_set.filter(**kwargs):
            users.append((membership.role, membership.user))
        return users

    def get_users_by_role(self, role):
        """
        Return all users of a questionnaire based on their role in the
        membership.

        Args:
            ``role`` (str): The role of the membership used as a filter.

        Returns:
            ``list``. A list of users.
        """
        users = []
        for user_role, user in self.get_users():
            if user_role == role:
                users.append(user)
        return users

    def add_user(self, user, role):
        """
        Add a user. Users are only added if the membership does not yet exist.

        Args:
            ``user`` (User): The user.

            ``role`` (str): The role of the user.
        """
        if self.get_user(user, role) is None:
            QuestionnaireMembership.objects.create(
                questionnaire=self, user=user, role=role)

    def remove_user(self, user, role):
        """
        Remove a user.

        Args:
            ``user`` (User): The user.

            ``role`` (str): The role of the user.
        """
        user = self.get_user(user, role)
        QuestionnaireMembership.objects.filter(
            questionnaire=self, user=user, role=role
        ).delete()

    def update_users_from_data(self, configuration_code):
        """
        Based on the data dictionary, update the user links in the
        database. This usually happens after the form of the
        questionnaire was submitted.

        Args:
            ``configuration_code`` (str): The code of the configuration
              of the questionnaire which triggered the update.

            ``compiler`` (accounts.models.User): A user figuring as the
            compiler of the questionnaire.
        """
        questionnaire_configuration = get_configuration(configuration_code)
        user_fields = questionnaire_configuration.get_user_fields()

        # Collect the users appearing in the data dictionary.
        submitted_users = []
        for user_questiongroup in user_fields:
            for user_data in self.data.get(user_questiongroup[0], []):
                user_id = user_data.get(user_questiongroup[1])
                if not bool(user_id):
                    continue
                submitted_users.append((user_questiongroup[3], user_id))

        # Get the users which were attached before modifying the
        # questionnaire. Collect only those which can be changed through
        # the data dictionary (no functional user roles)
        previous_users = []
        for user_role, user in self.get_users():
            if user_role not in [settings.QUESTIONNAIRE_COMPILER,
                                 settings.QUESTIONNAIRE_EDITOR,
                                 settings.QUESTIONNAIRE_REVIEWER,
                                 settings.QUESTIONNAIRE_PUBLISHER]:
                previous_users.append((user_role, user))

        # Check which users are new (in submitted_users but not in
        # previous_users) and add them to the questionnaire.
        previous_users_found = []
        for submitted_user in submitted_users:
            user_found = False
            for previous_user in previous_users:
                if submitted_user[0] != previous_user[0]:
                    continue
                if str(submitted_user[1]) != str(previous_user[1].id):
                    continue

                user_found = True
                previous_users_found.append(previous_user)

            if user_found is False:
                user = User.objects.get(pk=submitted_user[1])
                self.add_user(user, submitted_user[0])

        # Check for users which were removed (in previous_users but not
        # found when looking through submitted_users) and remove them
        # from the questionnaire
        for removed_user in list(
                set(previous_users) - set(previous_users_found)):
            self.remove_user(removed_user[1], removed_user[0])

    def get_metadata(self):
        """
        Return some metadata about the Questionnaire.

        Returns:
            ``dict``. A dict containing the following metadata:

            * ``created`` (timestamp)

            * ``updated`` (timestamp)

            * ``compilers`` (list): A list of dictionaries containing
              information about the compilers. Each entry contains the
              following data:

              * ``id``

              * ``name``

            * ``editors`` (list): A list of dictionaries containing information
            about the editors. The format is the same as for ``compilers``

            * ``code`` (string)

            * ``configurations`` (list)

            * ``translations`` (list)
        """
        return dict(self._get_metadata())

    def _get_metadata(self):
        # Access the property first, then the model field.
        for key in settings.QUESTIONNAIRE_METADATA_KEYS:
            yield key, getattr(self, '{}_property'.format(key),
                               getattr(self, key))

    def add_link(self, questionnaire, symm=True):
        """
        Add a link to another Questionnaire. This actually creates two
        entries in the link table to make the reference symmetrical.

        https://charlesleifer.com/blog/self-referencing-many-many-through/

        Args:
            ``questionnaire`` (questionnaire.models.Questionnaire): The
            questionnaire to link to.

        Kwargs:
            ``symm`` (bool): Whether or not to add the symmetrical link
            (to avoid recursion).

        Returns:
            ``questionnaire.models.Questionnaire``. The updated
            questionnaire.
        """
        link, created = QuestionnaireLink.objects.get_or_create(
            from_questionnaire=self,
            from_status=self.status,
            to_questionnaire=questionnaire,
            to_status=questionnaire.status)
        if symm:
            # avoid recursion by passing `symm=False`
            questionnaire.add_link(self, symm=False)
        return questionnaire

    def remove_link(self, questionnaire, symm=True):
        """
        Remove a link to another Questionnaire. This actually removes
        both links (also the symmetrical one).

        https://charlesleifer.com/blog/self-referencing-many-many-through/

        Args:
            ``questionnaire`` (questionnaire.models.Questionnaire): The
            questionnaire to remove.

        Kwargs:
            ``symm`` (bool): Whether or not to remove the symmetrical
            link (to avoid recursion).
        """
        QuestionnaireLink.objects.filter(
            from_questionnaire=self,
            to_questionnaire=questionnaire).delete()
        if symm:
            # avoid recursion by passing `symm=False`
            questionnaire.remove_link(self, symm=False)

    def __str__(self):
        return json.dumps(self.data)

    @classmethod
    def has_questionnaires_for_code(cls, code: str) -> bool:
        return cls.objects.filter(code=code).exists()

    @classmethod
    def lock_questionnaire(cls, code: str, user: settings.AUTH_USER_MODEL):
        """
        If the questionnaire is not locked, or locked by given user: lock the
        questionnaire for this user - else raise an error.

        """
        qs_locks = Lock.with_status.is_blocked(code, for_user=user)

        if qs_locks.exists():
            raise QuestionnaireLockedException(
                qs_locks.first().user
            )
        else:
            Lock.objects.create(questionnaire_code=code, user=user)

    def can_edit(self, user: settings.AUTH_USER_MODEL) -> bool:
        has_questionnaires = self.has_questionnaires_for_code(self.code)
        qs_locks = Lock.with_status.is_blocked(self.code, for_user=user)
        return has_questionnaires and not qs_locks.exists()

    def unlock_questionnaire(self):
        Lock.objects.filter(
            questionnaire_code=self.code
        ).update(
            is_finished=True
        )

    def get_blocked_message(self, user: settings.AUTH_USER_MODEL) -> tuple:
        """
        Get status and message for blocked status (blocked or can be edited).
        """
        locks = Lock.with_status.is_blocked(code=self.code, for_user=user)

        if not locks.exists():
            return SUCCESS, _(u"This questionnaire can be edited.")
        else:
            return WARNING, _(u"This questionnaire is "
                              u"locked for editing by {user}.".format(
                user=locks.first().user.get_display_name()
            ))

    # Properties for the get_metadata function.
    def _get_role_list(self, role):
        members = []
        for member in self.members.filter(questionnairemembership__role=role):
            members.append({
                'id': member.id,
                'name': str(member),
            })
        return members

    @cached_property
    def editors(self):
        return self._get_role_list(settings.QUESTIONNAIRE_EDITOR)

    @cached_property
    def compilers(self):
        return self._get_role_list(settings.QUESTIONNAIRE_COMPILER)

    @cached_property
    def status_property(self):
        status = next((x for x in STATUSES if x[0] == self.status), (None, ''))
        status_code = next(
            (x for x in STATUSES_CODES if x[0] == self.status), (None, ''))
        return status_code[1], status[1]

    @cached_property
    def configurations_property(self):
        return list(self.configurations.values_list('code', flat=True))

    def get_original_configuration(self):
        return self.configurations.filter(
            questionnaire__questionnaireconfiguration__original_configuration=True
        ).first()

    @cached_property
    def translations(self):
        return list(self.questionnairetranslation_set.values_list(
            'language', flat=True
        ))

    @cached_property
    def original_locale(self):
        translation = self.questionnairetranslation_set.filter(
            original_language=True).first()
        if translation:
            return translation.language
        else:
            return None

    @cached_property
    def links_property(self):
        """
        Collect all info about linked questionnaire and structure it according to language.
        This follows a often used pattern of questionnaire data.

        Returns: list

        """
        from configuration.utils import ConfigurationList

        links = []
        config_list = ConfigurationList()
        current_language = get_language()

        for link in self.links.filter(configurations__isnull=False).filter(
                status=settings.QUESTIONNAIRE_PUBLIC):

            link_configuration = config_list.get(link.configurations.first().code)
            name_data = link_configuration.get_questionnaire_name(link.data)

            try:
                original_language = link.questionnairetranslation_set.first().language
            except AttributeError:
                original_language = settings.LANGUAGES[0][0]  # 'en'

            names = {}
            urls = {}
            for code, language in settings.LANGUAGES:
                activate(code)
                names[code] = name_data.get(code, name_data.get(original_language))
                urls[code] = link.get_absolute_url()

                if code == original_language:
                    names['default'] = names[code]
                    urls['default'] = urls[code]

            links.append({
                'code': link.code,
                'configuration': link_configuration.keyword,
                'name': names,
                'url': urls,
            })

        activate(current_language)
        return links

    @cached_property
    def flags_property(self):
        flags = []
        for flag in self.flags.all():
            flags.append({
                'flag': flag.flag,
                'name': flag.get_flag_display(),
                'helptext': flag.get_helptext(),
            })
        return flags

    @cached_property
    def has_release(self):
        """
        Check if any version of this questionnaire was published.

        Returns: boolean

        """
        return self.status == settings.QUESTIONNAIRE_PUBLIC or self._meta.model.with_status.not_deleted().filter(
            code=self.code, status=settings.QUESTIONNAIRE_PUBLIC
        ).exists()


class QuestionnaireConfiguration(models.Model):
    """
    Represents a many-to-many relationship between Questionnaires and
    Configurations with additional fields. Additional fields mark the
    configuration in which the Questionnaire was originally entered.
    """
    questionnaire = models.ForeignKey('Questionnaire')
    configuration = models.ForeignKey('configuration.Configuration')
    original_configuration = models.BooleanField(default=False)

    class Meta:
        ordering = ['-original_configuration']


class QuestionnaireTranslation(models.Model):
    """
    Represents a many-to-many relationship between Questionnaires and
    languages with additional fields. Each translation of a
    Questionnaire gets an entry to allow a quick overview in which
    languages a Questionnaire is available. Additional fields mark the
    language in which the Questionnaire was originally entered.
    """
    questionnaire = models.ForeignKey('Questionnaire')
    language = models.CharField(max_length=63, choices=settings.LANGUAGES)
    original_language = models.BooleanField(default=False)

    class Meta:
        ordering = ['-original_language']


class Flag(models.Model):
    flag = models.CharField(max_length=64, choices=QUESTIONNAIRE_FLAGS)

    def get_helptext(self):
        return next((
            helptext for flag, helptext in QUESTIONNAIRE_FLAGS_HELPTEXT
            if flag == self.flag), None)


class QuestionnaireLink(models.Model):
    """

    """
    from_questionnaire = models.ForeignKey(
        'Questionnaire', related_name='from_questionnaire')
    from_status = models.IntegerField(choices=STATUSES)
    to_questionnaire = models.ForeignKey(
        'Questionnaire', related_name='to_questionnaire')
    to_status = models.IntegerField(choices=STATUSES)


class QuestionnaireMembership(models.Model):
    """
    The model representing the membership of a :class:`User` in a
    :class`Questionnaire` and his roles (:class:`QuestionnaireRole`).
    """
    questionnaire = models.ForeignKey('Questionnaire')
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    role = models.CharField(max_length=64, choices=QUESTIONNAIRE_ROLES)


class File(models.Model):
    """
    The model representing a file uploaded by a user.

    Please note that the file itself is not stored in the database, this
    model just contains the filenames of all of its thumbnails and some
    meta information (size, file type).
    """
    uuid = models.CharField(max_length=64)
    uploaded = models.DateTimeField(auto_now=True)
    content_type = models.CharField(max_length=64)
    size = models.BigIntegerField(null=True)
    thumbnails = JsonBField()

    @staticmethod
    def handle_upload(uploaded_file):
        """
        Handle the upload of a file by storing it, create thumbnails for it and
        create a database entry for it.

        The storage of the file is handled by :func:`store_file`.

        Args:
            uploaded_file (django.core.files.uploadedfile.UploadedFile):
            An uploaded file.

        Returns:
            The newly created File model instance.
        """
        file_uid, file_destination = store_file(uploaded_file)
        thumbnails = create_thumbnails(
            file_destination, uploaded_file.content_type)
        file_object = File.create_new(
            content_type=uploaded_file.content_type, size=uploaded_file.size,
            thumbnails=thumbnails, uuid=file_uid)
        return file_object

    @staticmethod
    def get_data(file_object=None, uid=None):
        """
        Get relevant data of a file.

        Args:
            file_object (questionnaire.models.File): A file model instance or
            None. If provided, no UID is necessary.

            uid (str): The UID of a file. If no file object is provided, the UID
            is required.

        Returns:
            dict. A dictionary with information about the file, namely:

            * content_type: The content type of the file.
            * interchange: The interchange URLs of the thumbnails, as string.
            * interchange_list: The interchange URLs of the thumbnails, as a
              list of tuples (URL, format).
            * size: The size of the file.
            * uid: The UID of the file.
            * url: The URL of the original file.
        """
        if file_object is None:
            try:
                file_object = File.objects.get(uuid=uid)
            except File.DoesNotExist:
                return {}

        interchange_list = []
        for thumbnail_format in settings.UPLOAD_IMAGE_THUMBNAIL_FORMATS:
            interchange_list.append(
                (file_object.get_url(thumbnail=thumbnail_format[0]),
                 thumbnail_format[0]))
        if file_object.content_type.split('/')[0] == 'image':
            # Only add large (pointing to the original file) if it is an image
            interchange_list.append((file_object.get_url(), 'large'))

        interchange_text = []
        for i_url, i_format in interchange_list:
            interchange_text.append('[{}, ({})]'.format(i_url, i_format))

        file_data = {
            'content_type': file_object.content_type,
            'interchange': interchange_text,
            'interchange_list': interchange_list,
            'size': file_object.size,
            'uid': str(file_object.uuid),
            'url': file_object.get_url(),
        }
        file_path, file_name = get_file_path(file_object)
        folder_structure = get_upload_folder_structure(file_object.uuid)
        if folder_structure:
            relative_path = join(*folder_structure)
            file_data.update({
                'absolute_path': file_path,
                'relative_path': join(relative_path, file_name),
            })
        return file_data

    @staticmethod
    def create_new(content_type, size=None, thumbnails=None, uuid=None):
        """
        Create and return a new file.

        Args:
            content_type (str): The mime type (e.g. ``image/png``) of the file.

            size (int): The size of the file.

            thumbnails (dict): A dictionary pointing to the
            thumbnails based on their predefined dimensions. Example::

              {
                "header_big": "e0791bc0-e05d-4a03-8ab9-f5f9c2615cac",
                "header_small": "23592f37-cd5b-43db-9376-04c5d805429d"
              }

            uuid (str): The UUID for the file. If not provided, a
            random UUID will be generated.

        Returns:
            ``questionnaire.models.File``. The created File model.
        """
        if uuid is None:
            uuid = uuid4()
        if thumbnails is None:
            thumbnails = {}
        return File.objects.create(
            uuid=uuid, content_type=content_type, size=size,
            thumbnails=thumbnails)

    def get_url(self, thumbnail=None):
        """
        Return the URL of a file object. If thumbnail is provided,
        return the respective URL.

        Args:
            thumbnail (str or None). The name of the thumbnail for
            which the URL shall be returned. If not specified, the
            original file will be returned.

        Returns:
            ``str`` or ``None``. The relative URL of the file object or
            ``None`` if the thumbnail was not found.
        """
        __, file_name = get_file_path(self, thumbnail=thumbnail)
        if file_name is None:
            return None
        return get_url_by_file_name(file_name)


class Lock(models.Model):
    """
    Locks questionnaire for editing. This collects more information than
    required, but does include info for debugging.
    This could be extended with a field for the questionnaires section.
    """
    questionnaire_code = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    start = models.DateTimeField(auto_now_add=True)
    is_finished = models.BooleanField(default=False)

    objects = models.Manager()
    with_status = LockStatusQuerySet.as_manager()
