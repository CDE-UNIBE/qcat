from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from model_mommy import mommy


from functional_tests.base import FunctionalTest
from notifications.models import Log
from wocat.tests.test_views import route_home


class MenuIndicatorTest(FunctionalTest):

    @patch('wocat.views.generic_questionnaire_list')
    def test_indicator(self, mock_list):
        mock_list.return_value = {}

        start_site_url = self.live_server_url + reverse(route_home)
        # Alice goes to the qcat start site
        self.browser.get(start_site_url)

        # Alice is not logged in, so no indicator is loaded.
        self.findByNot('class_name', 'notification-indicator')

        # After the login,
        user = mommy.make(get_user_model())
        self.doLogin(user=user)
        # there are not logs to be shown.
        self.findByNot('class_name', 'has-unread-messages')

        # Someone else triggers an action which creates a new task for Alice
        mommy.make(
            model=Log,
            catalyst=user,
            action=settings.NOTIFICATIONS_CHANGE_STATUS,
            _quantity=5
        )

        # so after loading the page agein, the indicator exists
        self.browser.get(start_site_url)

        link_element = self.findBy('class_name', 'has-unread-messages')
        self.assertEqual(
            link_element.text, '5'
        )

        # The link points to the notification list view.
        pending_url = '{base}{notification_list}?is_unread'.format(
            base=self.live_server_url,
            notification_list=reverse('notification_list')
        )
        self.assertEqual(
            link_element.get_attribute('href'), pending_url
        )
