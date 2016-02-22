from django.contrib.auth import get_user_model
from django.core.management import call_command

from qcat.tests import TestCase
User = get_user_model()


def create_new_user(id=1, email='a@b.com', lastname='foo', firstname='bar'):
    user, created = User.objects.get_or_create(
        id=id, email=email,
        defaults={'lastname': lastname, 'firstname': firstname}
    )
    return user


class SuperUserCommandTest(TestCase):
    """
    Tests for management commands.
    """
    def setUp(self):
        self.user = create_new_user()

    def tearDown(self):
        self.user.delete()

    def test_command_set_one_superuser(self):
        self.assertFalse(self.user.is_superuser)
        call_command('set_superuser', 'a@b.com')
        # Refresh the object, as it was changed externally.
        self.user.refresh_from_db(fields=['is_superuser'])
        self.assertTrue(self.user.is_superuser)

    def test_command_set_multiple_superusers(self):
        make_superuser = ['foo@bar.com', 'bar@baz.com']

        for index, email in enumerate(make_superuser):
            create_new_user(id=index + 5, email=email)

        call_command('set_superuser', *make_superuser)

        superuser_emails = get_user_model().objects.filter(
            is_superuser=True
        ).values_list('email', flat=True)

        self.assertListEqual(list(superuser_emails), make_superuser)
