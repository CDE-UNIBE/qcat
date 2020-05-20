from django.conf import settings
from rest_framework.permissions import IsAuthenticated

from qcat.tests import TestCase
from questionnaire.api.views import QuestionnaireListView

from django.contrib.auth import get_user_model
from accounts.tests.test_authentication import get_mock_user_information_values
User = get_user_model()


class ApiViewTest(TestCase):
    """
    The largest part of the API is just configuration.
    """

    def test_permission_required(self):
        # Ensure required authentication.
        settings.DEBUG = False
        permissions = QuestionnaireListView().get_permissions()
        self.assertIsInstance(permissions[0], IsAuthenticated)

    # def test_apptoken_obtain(self):
    #     """
    #     Test if a user can obtain a auth token
    #     """
    #     settings.DEBUG = False
    #     user_info = get_mock_user_information_values()
    #     User.objects.create(id=user_info['pk'], email=user_info['email'])


