import json
import logging
import uuid
from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.geos import GeometryCollection, GEOSGeometry
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils.translation import activate
from unittest.mock import patch, Mock

from accounts.models import User
from accounts.tests.test_models import create_new_user
from configuration.models import Configuration
from qcat.tests import TestCase
from questionnaire.errors import QuestionnaireLockedException
from questionnaire.models import Questionnaire, QuestionnaireLink, File, Lock

from ..conf import settings


def get_valid_file():
    return File.create_new(
        content_type='content_type', size=0, thumbnails={
            "header_1": "foo", "header_2": "bar"}, uuid=uuid.uuid4())


def get_valid_questionnaire(user=None):
    """
    Assumes fixture 'sample.json' is loaded
    """
    if user is None:
        user = create_new_user()
    return Questionnaire.create_new(
        configuration_code='sample', data={'foo': 'bar'},
        user=user)


def get_valid_metadata():
    return {
        'created': 'created',
        'updated': 'updated',
        'compilers': ['compiler'],
        'editors': ['editor'],
        'code': 'code',
        'configurations': ['configuration'],
        'translations': ['en']
    }


class QuestionnaireModelTest(TestCase):

    fixtures = ['sample.json', 'sample_global_key_values.json']

    def setUp(self):
        self.user = create_new_user()

    def test_requires_data(self):
        questionnaire = Questionnaire()
        with self.assertRaises(ValidationError):
            questionnaire.full_clean()

    def test_has_primary_key(self):
        questionnaire = Questionnaire(data={})
        self.assertTrue(hasattr(questionnaire, 'id'))

    def test_has_uuid(self):
        questionnaire = Questionnaire(data={})
        self.assertIsInstance(questionnaire.uuid, uuid.UUID)

    def test_create_new_returns_new_object(self):
        returned = Questionnaire.create_new(
            configuration_code='sample', data={'foo': 'bar'}, user=self.user)
        new_questionnaire = Questionnaire.objects.get(pk=returned.id)
        self.assertEqual(returned, new_questionnaire)

    def test_create_new_sets_data(self):
        questionnaire = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user)
        self.assertEqual(questionnaire.data, {})

    def test_create_new_sets_status(self):
        questionnaire = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user, status=2)
        self.assertEqual(questionnaire.status, 2)

    def test_create_new_sets_default_status(self):
        questionnaire = get_valid_questionnaire(self.user)
        self.assertEqual(questionnaire.status, 1)

    def test_create_new_sets_default_created(self):
        questionnaire = get_valid_questionnaire(self.user)
        self.assertIsNotNone(questionnaire.created)

    def test_create_new_sets_created(self):
        date = datetime.now()
        questionnaire = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user, created=date)
        self.assertEqual(questionnaire.created, date)

    def test_previous_version_only_allows_certain_status(self):
        previous = Questionnaire(status=2)
        with self.assertRaises(ValidationError):
            Questionnaire.create_new(
                configuration_code='sample', data={}, user=self.user,
                previous_version=previous)

    def test_previous_version_pending_updates_same_questionnaire(self):
        previous = get_valid_questionnaire(self.user)
        previous.status = 1
        q = Questionnaire.create_new(
            configuration_code='sample', data={'faz': 'taz'}, user=self.user,
            previous_version=previous)
        self.assertEqual(q, previous)
        self.assertEqual(previous.data, {'faz': 'taz'})

    def test_previous_version_public_keeps_same_code(self):
        previous = get_valid_questionnaire(self.user)
        previous.status = 4
        q = Questionnaire.create_new(
            configuration_code='sample', data={'faz': 'taz'}, user=self.user,
            previous_version=previous)
        self.assertNotEqual(q, previous)
        self.assertEqual(q.code, previous.code)
        self.assertEqual(q.version, previous.version + 1)

    def test_create_new_keeps_languages_from_previous_version(self):
        previous = get_valid_questionnaire(self.user)
        previous.status = 4
        previous.add_translation_language(language='fr')
        previous.add_translation_language(language='es')
        self.assertEqual(len(previous.translations), 3)
        self.assertEqual(previous.original_locale, 'en')
        q = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user,
            previous_version=previous)
        self.assertEqual(len(q.translations), 3)
        self.assertEqual(q.original_locale, 'en')
        self.assertEqual(previous.translations, q.translations)

    def test_create_new_keeps_users_from_previous_version(self):
        user2 = create_new_user(
            id=2, email='c@d.com', lastname='foo2', firstname='bar2')
        user3 = create_new_user(
            id=3, email='e@f.com', lastname='foo3', firstname='bar3')
        previous = get_valid_questionnaire(self.user)
        previous.status = 4
        previous.add_user(user2, settings.QUESTIONNAIRE_EDITOR)
        previous.add_user(user3, settings.QUESTIONNAIRE_REVIEWER)
        previous_users = previous.get_users()
        self.assertEqual(len(previous_users), 3)
        self.assertIn(
            (settings.QUESTIONNAIRE_COMPILER, self.user), previous_users)
        self.assertIn((settings.QUESTIONNAIRE_EDITOR, user2), previous_users)
        self.assertIn((settings.QUESTIONNAIRE_REVIEWER, user3), previous_users)
        # Compiler starts a new version
        q = Questionnaire.create_new(
            configuration_code='sample', data={}, user=user2,
            previous_version=previous)
        current_users = q.get_users()
        self.assertEqual(len(current_users), 3)
        self.assertEqual(current_users, previous_users)

    @patch('configuration.utils.create_new_code')
    def test_create_new_calls_create_code(self, mock_create_new_code):
        mock_create_new_code.return_value = 'foo'
        get_valid_questionnaire(self.user)
        mock_create_new_code.assert_called_once_with('sample', {'foo': 'bar'})

    def test_create_new_raises_error_if_invalid_status(self):
        with self.assertRaises(ValidationError):
            Questionnaire.create_new(
                configuration_code='sample', data={}, user=self.user,
                status=-1)

    def test_create_new_sets_default_version(self):
        questionnaire = get_valid_questionnaire(self.user)
        self.assertEqual(questionnaire.version, 1)

    def test_create_new_raises_error_if_no_active_configuration(self):
        with self.assertRaises(ValidationError):
            Questionnaire.create_new(
                configuration_code='foo', data={}, user=self.user)

    def test_create_new_adds_configuration(self):
        configuration = Configuration.get_active_by_code('sample')
        ret = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user)
        ret_configurations = ret.configurations.all()
        self.assertEqual(len(ret_configurations), 1)
        self.assertEqual(ret_configurations[0].id, configuration.id)

    @patch('questionnaire.models.get_language')
    def test_create_new_calls_get_language(self, mock_get_language):
        Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user)
        mock_get_language.assert_called_once_with()

    def test_create_new_adds_language(self):
        language = 'en'
        ret = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user)
        ret_languages = ret.questionnairetranslation_set.all()
        self.assertEqual(len(ret_languages), 1)
        self.assertEqual(ret_languages[0].language, language)

    def test_create_new_adds_language2(self):
        language = 'es'
        activate('es')
        ret = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user)
        ret_languages = ret.questionnairetranslation_set.all()
        self.assertEqual(len(ret_languages), 1)
        self.assertEqual(ret_languages[0].language, language)
        activate('en')

    @patch.object(Questionnaire, 'update_users_from_data')
    def test_create_new_calls_update_users_from_data(self, mock_foo):
        get_valid_questionnaire(self.user)
        mock_foo.assert_called_once_with('sample')

    def test_create_new_adds_compiler(self):
        questionnaire = get_valid_questionnaire(self.user)
        users = questionnaire.get_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0], ('compiler', self.user))

    def test_create_new_copies_compilers(self):
        questionnaire = get_valid_questionnaire(self.user)
        user_2 = create_new_user(id=2, email='foo@bar.com')
        user_3 = create_new_user(id=3, email='faz@bar.com')
        questionnaire.add_user(user_2, 'compiler')
        questionnaire.add_user(user_3, 'editor')
        questionnaire.status = 4
        users = questionnaire.get_users()
        self.assertEqual(len(users), 3)
        questionnaire_2 = Questionnaire.create_new(
            configuration_code='sample', data=questionnaire.data,
            user=self.user, previous_version=questionnaire)
        self.assertEqual(users, questionnaire_2.get_users())

    def test_get_roles_permissions_returns_empty(self):
        other_user = create_new_user(
            id=2, email='c@d.com', lastname='faz', firstname='taz')
        questionnaire = get_valid_questionnaire(other_user)
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [])
        self.assertEqual(permissions, [])

    def test_get_permissions_returns_empty_permission_not_found(self):
        questionnaire = get_valid_questionnaire(self.user)
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'foo'
        membership.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [])
        self.assertEqual(permissions, [])

    def test_get_roles_permissions_returns_compiler_draft(self):
        questionnaire = get_valid_questionnaire(self.user)
        self.assertEqual(questionnaire.status, 1)
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('compiler', 'Compiler')])
        self.assertEqual(len(permissions), 4)
        self.assertIn('edit_questionnaire', permissions)
        self.assertIn('delete_questionnaire', permissions)
        self.assertIn('submit_questionnaire', permissions)
        self.assertIn('assign_questionnaire', permissions)

    def test_roles_permissions_returns_no_compiler_submitted(self):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 2
        questionnaire.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [])
        self.assertEqual(permissions, [])

    def test_get_permissions_editors(self):
        questionnaire = get_valid_questionnaire(self.user)
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'editor'
        membership.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('editor', 'Editor')])
        self.assertEqual(permissions, ['edit_questionnaire'])

    def test_get_permissions_reviewers_not_status(self):
        questionnaire = get_valid_questionnaire(self.user)
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'reviewer'
        membership.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [])
        self.assertEqual(permissions, [])

    def test_get_permissions_reviewers(self):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 2
        questionnaire.save()
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'reviewer'
        membership.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('reviewer', 'Reviewer')])
        self.assertEqual(len(permissions), 2)
        self.assertIn('edit_questionnaire', permissions)
        self.assertIn('review_questionnaire', permissions)

    def test_get_permissions_publishers_not_status(self):
        questionnaire = get_valid_questionnaire(self.user)
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'publisher'
        membership.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [])
        self.assertEqual(permissions, [])

    def test_get_permissions_publishers(self):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 3
        questionnaire.save()
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'publisher'
        membership.save()
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('publisher', 'Publisher')])
        self.assertEqual(len(permissions), 2)
        self.assertIn('edit_questionnaire', permissions)
        self.assertIn('publish_questionnaire', permissions)

    @patch.object(User, 'get_all_permissions')
    def test_get_permissions_reviewers_general(self, mock_get_all_permissions):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 2
        questionnaire.save()
        mock_get_all_permissions.return_value = [
            'questionnaire.review_questionnaire']
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('reviewer', 'Reviewer')])
        self.assertEqual(len(permissions), 2)
        self.assertIn('edit_questionnaire', permissions)
        self.assertIn('review_questionnaire', permissions)

    @patch.object(User, 'get_all_permissions')
    def test_get_permissions_reviewers_general_and_assigned(
            self, mock_get_all_permissions):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 2
        questionnaire.save()
        membership = questionnaire.questionnairemembership_set.first()
        membership.role = 'reviewer'
        membership.save()
        mock_get_all_permissions.return_value = [
            'questionnaire.review_questionnaire']
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('reviewer', 'Reviewer')])
        self.assertEqual(len(permissions), 2)
        self.assertIn('edit_questionnaire', permissions)
        self.assertIn('review_questionnaire', permissions)

    @patch.object(User, 'get_all_permissions')
    def test_get_permissions_publishers_general(
            self, mock_get_all_permissions):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 3
        questionnaire.save()
        mock_get_all_permissions.return_value = [
            'questionnaire.publish_questionnaire']
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('publisher', 'Publisher')])
        self.assertEqual(len(permissions), 2)
        self.assertIn('edit_questionnaire', permissions)
        self.assertIn('publish_questionnaire', permissions)

    @patch.object(User, 'get_all_permissions')
    def test_get_permissions_wocat_secretariat(
            self, mock_get_all_permissions):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.status = 3
        questionnaire.save()
        mock_get_all_permissions.return_value = [
            'questionnaire.assign_questionnaire']
        roles, permissions = questionnaire.get_roles_permissions(self.user)
        self.assertEqual(roles, [('secretariat', 'WOCAT Secretariat')])
        expected_permissions = ['assign_questionnaire', 'review_questionnaire',
                                'delete_questionnaire', 'submit_questionnaire',
                                'edit_questionnaire', 'publish_questionnaire']
        self.assertTrue(
            len(permissions) == len(expected_permissions) and sorted(
                permissions) == sorted(expected_permissions))

    def test_get_permissions_anonymous_user(self):
        # Anonymous users have no rights.
        questionnaire = get_valid_questionnaire()
        user = AnonymousUser()
        roles, permissions = questionnaire.get_roles_permissions(user)
        self.assertEqual(roles, [])
        self.assertEqual(permissions, [])

    def test_get_users_returns_tuples(self):
        questionnaire = get_valid_questionnaire(self.user)
        users = questionnaire.get_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0][0], 'compiler')
        self.assertEqual(users[0][1], self.user)

    def test_add_user_adds_user(self):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.add_user(self.user, 'landuser')
        users = questionnaire.get_users()
        self.assertEqual(len(users), 2)
        for role, user in users:
            self.assertIn(role, ['compiler', 'landuser'])
            self.assertIn(user, [self.user])

    def test_add_user_adds_user_only_once(self):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.add_user(self.user, 'landuser')
        questionnaire.add_user(self.user, 'landuser')
        users = questionnaire.get_users()
        self.assertEqual(len(users), 2)
        for role, user in users:
            self.assertIn(role, ['compiler', 'landuser'])
            self.assertIn(user, [self.user])

    def test_remove_user_removes_user(self):
        questionnaire = get_valid_questionnaire(self.user)
        questionnaire.remove_user(self.user, 'compiler')
        users = questionnaire.get_users()
        self.assertEqual(len(users), 0)

    def test_update_users_from_data_does_not_affect_compilers(self):
        questionnaire = get_valid_questionnaire(self.user)
        users = questionnaire.get_users()
        questionnaire.update_users_from_data('sample')
        self.assertEqual(users, questionnaire.get_users())

    def test_update_users_from_data_adds_user_from_data(self):
        questionnaire = get_valid_questionnaire(self.user)
        user_2 = create_new_user(id=2, email='foo@bar.com')
        questionnaire.data = {'qg_31': [{'key_39': '2', 'key_40': 'Foo Bar'}]}
        questionnaire.update_users_from_data('sample')
        users = questionnaire.get_users()
        self.assertEqual(len(users), 2)
        for role, user in users:
            self.assertIn(role, ['compiler', 'landuser'])
            self.assertIn(user, [self.user, user_2])

    def test_update_users_from_data_removes_user_from_data(self):
        questionnaire = get_valid_questionnaire(self.user)
        user_2 = create_new_user(id=2, email='foo@bar.com')
        questionnaire.add_user(user_2, 'landuser')
        questionnaire.update_users_from_data('sample')
        users = questionnaire.get_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0][0], 'compiler')
        self.assertEqual(users[0][1], self.user)

    def test_get_metadata(self):
        questionnaire = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user)
        metadata = questionnaire.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual(len(metadata), 10)
        self.assertEqual(metadata['created'], questionnaire.created)
        self.assertEqual(metadata['updated'], questionnaire.updated)
        self.assertEqual(
            metadata['compilers'],
            [{'id': self.user.id, 'name': str(self.user)}])
        self.assertEqual(metadata['editors'], [])
        self.assertEqual(metadata['code'], questionnaire.code)
        self.assertEqual(metadata['configurations'], ['sample'])
        self.assertEqual(metadata['translations'], ['en'])
        self.assertEqual(metadata['status'], ('draft', 'Draft'))
        self.assertEqual(metadata['flags'], [])

    def test_has_links(self):
        questionnaire = get_valid_questionnaire(self.user)
        self.assertEqual(questionnaire.links.count(), 0)

    def test_add_link_creates_link(self):
        self.assertEqual(QuestionnaireLink.objects.count(), 0)
        questionnaire_1 = get_valid_questionnaire(self.user)
        questionnaire_2 = get_valid_questionnaire(self.user)
        questionnaire_1.add_link(questionnaire_2)
        self.assertEqual(questionnaire_1.links.count(), 1)
        self.assertEqual(QuestionnaireLink.objects.count(), 2)
        self.assertEqual(questionnaire_1.links.first(), questionnaire_2)
        self.assertEqual(questionnaire_2.links.first(), questionnaire_1)

    def test_remove_link_removes_link(self):
        questionnaire_1 = get_valid_questionnaire(self.user)
        questionnaire_2 = get_valid_questionnaire(self.user)
        questionnaire_1.add_link(questionnaire_2)
        self.assertEqual(questionnaire_2.links.count(), 1)
        self.assertEqual(QuestionnaireLink.objects.count(), 2)
        questionnaire_2.remove_link(questionnaire_1)
        self.assertEqual(questionnaire_2.links.count(), 0)
        self.assertEqual(QuestionnaireLink.objects.count(), 0)

    @patch.object(Questionnaire, 'update_geometry')
    def test_protect_published_item(self, mock_update_geometry):
        questionnaire = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user, status=4
        )
        self.assertEqual(questionnaire.status, 4)
        questionnaire.data = {'foo': 'bar'}
        self.assertRaises(ValidationError, lambda: questionnaire.save())

    def test_allow_changes_unpublished_item(self):
        questionnaire = Questionnaire.create_new(
            configuration_code='sample', data={}, user=self.user, status=1
        )
        questionnaire.data = {'foo': 'bar'}
        questionnaire.save()
        self.assertEqual(questionnaire.data, {'foo': 'bar'})

    def test_block_for_for_user(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.lock_questionnaire(
            code=questionnaire.code,
            user=self.user
        )
        lock = Lock.with_status.is_blocked(code=questionnaire.code)
        self.assertEqual(
            lock.first().user, self.user
        )

    def test_blocked_questionnaire_raises_exception(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.lock_questionnaire(questionnaire.code, self.user)
        user_2 = create_new_user(id=2, email='foo@bar.com')
        with self.assertRaises(QuestionnaireLockedException):
            questionnaire.lock_questionnaire(questionnaire.code, user_2)

    def test_blocked_allow_editing_for_same_user(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.lock_questionnaire(questionnaire.code, self.user)
        self.assertTrue(questionnaire.can_edit(self.user))

    def test_blocked_for_other_user(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.lock_questionnaire(questionnaire.code, self.user)
        user_2 = create_new_user(id=2, email='foo@bar.com')
        self.assertFalse(questionnaire.can_edit(user_2))

    def test_update_geometry_updates_geometry(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.data = {'qg_39': [{'key_56': json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            7.5,
                            47
                        ]
                    },
                },
               {
                   "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            8.5,
                            48
                        ]
                    },
               }
            ]
        })}]}
        questionnaire.save()
        self.assertIsNone(questionnaire.geom)
        questionnaire.update_geometry('sample')
        geojson = json.loads(questionnaire.geom.geojson)
        self.assertEqual(len(geojson['geometries']), 2)
        self.assertEqual(geojson['geometries'][0]['coordinates'], [7.5, 47.0])
        self.assertEqual(geojson['geometries'][1]['coordinates'], [8.5, 48.0])

    def test_update_geometry_handles_no_geometry(self):
        questionnaire = get_valid_questionnaire()
        self.assertIsNone(questionnaire.geom)
        questionnaire.update_geometry('sample')
        self.assertIsNone(questionnaire.geom)

    def test_update_geometry_handles_invalid_geometry(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.data = {'qg_39': [{'key_56': 'invalid geometry'}]}
        questionnaire.save()
        self.assertIsNone(questionnaire.geom)
        questionnaire.update_geometry('sample')
        self.assertIsNone(questionnaire.geom)

    def test_update_geometry_handles_invalid_geojson(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.data = {'qg_39': [{'key_56': json.dumps({'foo': 'bar'})}]}
        questionnaire.save()
        self.assertIsNone(questionnaire.geom)
        questionnaire.update_geometry('sample')
        self.assertIsNone(questionnaire.geom)

    def test_update_geometry_handles_invalid_geojson_2(self):
        logging.disable(logging.CRITICAL)
        questionnaire = get_valid_questionnaire()
        questionnaire.data = {'qg_39': [{'key_56': json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": "invalid",
                },
               {
                   "type": "Foo",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            "foo",
                            "bar"
                        ]
                    },
               }
            ]
        })}]}
        questionnaire.save()
        self.assertIsNone(questionnaire.geom)
        questionnaire.update_geometry('sample')
        self.assertIsNone(questionnaire.geom)

    def test_update_geometry_deletes_geometry(self):
        questionnaire = get_valid_questionnaire()

        geojson = {'coordinates': [7.435190677642821, 46.952664413488606],
                   'type': 'Point'}
        questionnaire.geom = GeometryCollection(
            GEOSGeometry(json.dumps(geojson)),)
        questionnaire.save()
        questionnaire.data = {}
        questionnaire.save()
        self.assertIsNotNone(questionnaire.geom)
        questionnaire.update_geometry('sample')
        self.assertIsNone(questionnaire.geom)

    def test_add_translation_language_original(self):
        questionnaire = get_valid_questionnaire()
        translations = questionnaire.translations
        self.assertEqual(translations, ['en'])
        activate('es')
        questionnaire = get_valid_questionnaire()
        translations = questionnaire.translations
        self.assertEqual(translations, ['es'])
        activate('en')

    def test_add_translation_language_not_original(self):
        activate('es')
        questionnaire = get_valid_questionnaire()
        translations = questionnaire.translations
        self.assertEqual(translations, ['es'])
        activate('en')
        questionnaire.add_translation_language(original=False)
        translations = questionnaire.translations
        self.assertEqual(len(translations), 2)
        self.assertEqual(translations, ['es', 'en'])

    def test_add_translation_language_adds_only_once(self):
        questionnaire = get_valid_questionnaire()
        questionnaire.add_translation_language(original=False)
        questionnaire.add_translation_language(original=False)
        translations = questionnaire.translations
        self.assertEqual(len(translations), 1)
        self.assertEqual(translations, ['en'])
    def test_links_property_returns_list(self):
        questionnaire_1 = get_valid_questionnaire()
        questionnaire_2 = get_valid_questionnaire()
        questionnaire_1.add_link(questionnaire_2)
        links_property = questionnaire_1.links_property
        self.assertTrue(isinstance(links_property, list))

    @override_settings(LANGUAGES=(('en', 'English'), ('es', 'Spanish')))
    def test_links_property_adds_each_name(self):
        questionnaire_1 = get_valid_questionnaire()
        questionnaire_1.status = 4
        questionnaire_1.save()
        questionnaire_2 = get_valid_questionnaire()
        questionnaire_2.status = 4
        questionnaire_2.save()
        questionnaire_1.add_link(questionnaire_2)
        links_property = questionnaire_1.links_property
        link_names = links_property[0]['name']
        self.assertEqual(len(link_names), 3)
        self.assertEqual(link_names['default'], 'Unknown name')
        self.assertEqual(link_names['en'], 'Unknown name')
        self.assertEqual(link_names['es'], 'Unknown name')

    @override_settings(LANGUAGES=(('en', 'English'), ('es', 'Spanish')))
    def test_links_property_adds_each_url(self):
        questionnaire_1 = get_valid_questionnaire()
        questionnaire_1.status = 4
        questionnaire_1.save()
        questionnaire_2 = get_valid_questionnaire()
        questionnaire_2.status = 4
        questionnaire_2.save()
        questionnaire_1.add_link(questionnaire_2)
        links_property = questionnaire_1.links_property
        link_urls = links_property[0]['url']
        self.assertEqual(len(link_urls), 3)
        activate('es')
        self.assertEqual(link_urls['es'], reverse(
            'sample:questionnaire_details', kwargs={'identifier': 'sample_1'}))
        activate('en')
        en_url = reverse(
            'sample:questionnaire_details', kwargs={'identifier': 'sample_1'})
        self.assertEqual(link_urls['default'], en_url)
        self.assertEqual(link_urls['en'], en_url)

    def test_links_property_only_returns_public_links(self):
        questionnaire_1 = get_valid_questionnaire()
        questionnaire_1.status = 4
        questionnaire_1.save()
        questionnaire_2 = get_valid_questionnaire()
        questionnaire_2.status = 4
        questionnaire_2.save()
        questionnaire_3 = get_valid_questionnaire()
        questionnaire_3.status = 1
        questionnaire_3.save()
        questionnaire_1.add_link(questionnaire_2)
        questionnaire_1.add_link(questionnaire_3)
        links_property = questionnaire_1.links_property
        self.assertEqual(len(links_property), 1)

class FileModelTest(TestCase):

    def test_requires_uuid(self):
        file = File(content_type='foo/bar')
        with self.assertRaises(ValidationError):
            file.full_clean()

    def test_requires_mime_type(self):
        file = File(uuid=uuid.uuid4())
        with self.assertRaises(ValidationError):
            file.full_clean()

    def test_has_primary_key(self):
        file = File()
        self.assertTrue(hasattr(file, 'id'))

    def test_get_valid_file_is_valid(self):
        file = get_valid_file()
        file.full_clean()  # Should not raise

    def test_create_new_returns_new_object(self):
        ret = File.create_new(content_type='foo/bar')
        q = File.objects.get(pk=ret.id)
        self.assertEqual(ret, q)

    def test_create_new_sets_uuid_if_not_set(self):
        file = File.create_new(content_type='foo/bar')
        self.assertIsInstance(file.uuid, uuid.UUID)

    @patch('questionnaire.models.get_file_path')
    def test_get_url_calls_get_file_path(self, mock_get_file_path):
        mock_get_file_path.return_value = None, None
        file = get_valid_file()
        file.get_url(thumbnail='thumb')
        mock_get_file_path.assert_called_once_with(file, thumbnail='thumb')

    @patch('questionnaire.models.get_file_path')
    def test_get_url_returns_none_if_file_name_none(self, mock_get_file_path):
        mock_get_file_path.return_value = None, None
        file = get_valid_file()
        res = file.get_url()
        self.assertIsNone(res)

    @patch('questionnaire.models.get_url_by_file_name')
    @patch('questionnaire.models.get_file_path')
    def test_get_url_calls_get_url_by_filename(
            self, mock_get_file_path, mock_get_url_by_file_name):
        mock_get_file_path.return_value = None, Mock()
        file = get_valid_file()
        file.get_url()
        mock_get_url_by_file_name.assert_called_once_with(
            mock_get_file_path.return_value[1])

    @patch.object(File, 'create_new')
    @patch('questionnaire.models.create_thumbnails')
    @patch('questionnaire.models.store_file')
    def test_handle_upload_calls_store_file(
            self, mock_store_file, mock_create_thumbnails, mock_create_new):
        mock_store_file.return_value = 'uid', 'dest'
        mock_file = Mock()
        File.handle_upload(mock_file)
        mock_store_file.assert_called_once_with(mock_file)

    @patch.object(File, 'create_new')
    @patch('questionnaire.models.create_thumbnails')
    @patch('questionnaire.models.store_file')
    def test_handle_upload_calls_create_thumbnails(
            self, mock_store_file, mock_create_thumbnails, mock_create_new):
        mock_store_file.return_value = 'uid', 'dest'
        mock_file = Mock()
        File.handle_upload(mock_file)
        mock_create_thumbnails.assert_called_once_with(
            'dest', mock_file.content_type)

    @patch.object(File, 'create_new')
    @patch('questionnaire.models.create_thumbnails')
    @patch('questionnaire.models.store_file')
    def test_handle_upload_calls_create_new(
            self, mock_store_file, mock_create_thumbnails, mock_create_new):
        mock_store_file.return_value = 'uid', 'dest'
        mock_file = Mock()
        File.handle_upload(mock_file)
        mock_create_new.assert_called_once_with(
            content_type=mock_file.content_type, size=mock_file.size,
            thumbnails=mock_create_thumbnails.return_value, uuid='uid'
        )

    @patch.object(File.objects, 'get')
    def test_get_data_gets_object_if_not_provided(self, mock_objects_get):
        mock_objects_get.return_value = get_valid_file()
        File.get_data(file_object=None, uid='uid')
        mock_objects_get.assert_called_once_with(uuid='uid')

    def test_get_data_returns_empty_if_no_file_found(self):
        ret = File.get_data(file_object=None, uid='uid')
        self.assertEqual(ret, {})

    def test_returns_file_data(self):
        file = get_valid_file()
        ret = File.get_data(file_object=file)
        self.assertEqual(len(ret), 6)
        self.assertEqual(ret['content_type'], file.content_type)
        self.assertEqual(len(ret['interchange']), 3)
        self.assertIsInstance(ret['interchange'][0], str)
        self.assertEqual(len(ret['interchange_list']), 3)
        self.assertIsInstance(ret['interchange_list'][0], tuple)
        self.assertEqual(ret['size'], file.size)
        self.assertEqual(ret['uid'], str(file.uuid))
        self.assertIn('url', ret)
