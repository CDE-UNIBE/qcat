from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from qcat.tests import TestCase
User = get_user_model()


def create_new_user(id=1, email='a@b.com', lastname='foo', firstname='bar'):
    user, created = User.objects.get_or_create(
        id=id, email=email,
        defaults={'lastname': lastname, 'firstname': firstname}
    )
    return user


class UserModelTestWithFixtures(TestCase):
    fixtures = ['groups_permissions.json']

    def test_administrator_is_staff(self):
        user = create_new_user()
        user.groups.add(Group.objects.get(name='Administrators'))
        self.assertTrue(user.is_staff)

    def test_translator_is_staff(self):
        user = create_new_user()
        user.groups.add(Group.objects.get(name='Translators'))
        self.assertTrue(user.is_staff)


class UserModelTest(TestCase):

    def test_cannot_have_empty_email(self):
        user = User(email=None, password='foo')
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_cannot_have_empty_password(self):
        user = User(email='a@b.com', password='')
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_id_is_primary_key(self):
        user = User()
        self.assertTrue(hasattr(user, 'id'))

    def test_is_authenticated(self):
        user = User()
        self.assertTrue(user.is_authenticated())

    def test_is_active(self):
        user = User()
        self.assertTrue(user.is_active)

    def test_is_not_staff(self):
        user = User.create_new(id=1, email='a@b.com', lastname='foo')
        self.assertFalse(user.is_staff)

    def test_superuser_is_staff(self):
        user = User()
        user.is_superuser = True
        self.assertTrue(user.is_staff)

    def test_get_full_name(self):
        user = User()
        self.assertEqual(user.email, user.get_full_name())

    def test_get_short_name(self):
        user = User()
        self.assertEqual(user.email, user.get_short_name())

    def test_user_str(self):
        user = User()
        self.assertEqual(
            '{} {}'.format(user.firstname, user.lastname), str(user))

    def test_create_new_returns_new_object(self):
        returned = User.create_new(id=1, email='a@b.com')
        new_user = User.objects.get(email='a@b.com')
        self.assertEqual(returned, new_user)

    def test_create_new_without_password(self):
        user = User.create_new(id=1, email='a@b.com')
        self.assertEqual(user.password, '')

    def test_create_new_sets_name(self):
        user = User.create_new(id=1, email='a@b.com', lastname='Foo')
        self.assertEqual(user.lastname, 'Foo')

    def test_update_updates_name(self):
        user = User.create_new(id=1, email='a@b.com', lastname='Foo')
        user.update(lastname='Bar')
        self.assertEqual(user.lastname, 'Bar')


class UserModelTestFixtures(TestCase):

    fixtures = ['sample.json']

    def test_get_questionnaires_returns_tuples(self):
        from questionnaire.tests.test_models import get_valid_questionnaire
        user = create_new_user(id=3, email='foo@bar.com')
        questionnaire_1 = get_valid_questionnaire(user=user)
        questionnaire_2 = get_valid_questionnaire()
        questionnaire_2.add_user(user, 'landuser')
        ret = user.get_questionnaires()
        self.assertEqual(len(ret), 2)
        for role, questionnaire in ret:
            self.assertIn(role, ['compiler', 'landuser'])
            self.assertIn(questionnaire, [questionnaire_1, questionnaire_2])
