from io import StringIO
from django.core.management import call_command
from qcat.tests import TestCase


class MigrationMissingTest(TestCase):
    """
    Check missing migrations; adapted from
    http://tech.octopus.energy/2016/01/21/testing-for-missing-migrations-in-django.html  # noqa
    """

    def setUp(self):
        pass

    def test_for_missing_migrations(self):
        output = StringIO()
        try:
            call_command('makemigrations', interactive=False, dry_run=True,
                         exit_code=True, stdout=output)
        except SystemExit as e:
            # The exit code will be 1 when there are no missing migrations
            self.assertEqual(str(e), '1')
        else:
            self.assertFalse(
                False, "There are missing migrations:\n %s" % output.getvalue()
            )
