import contextlib
import logging
from datetime import datetime
from typing import Union
from os.path import isfile

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


def template_settings(request):
    """
    Put selected setting variables to the template and check for maintenance
    announcements
    """
    maintenance_announcement = MaintenanceAnnouncement(request)

    setting_values = [
        'GOOGLE_WEBMASTER_TOOLS_KEY',
        'GOOGLE_MAPS_JAVASCRIPT_API_KEY',
        'IS_ACTIVE_FEATURE_MODULE',
        'IS_ACTIVE_FEATURE_WATERSHED',
        'PIWIK_URL',
        'PIWIK_SITE_ID',
        'WARN_HEADER',
        'WORD_WRAP_LANGUAGES'
    ]
    return {
        **maintenance_announcement.overlay,
        **{value: getattr(settings, value) for value in setting_values}
    }


class MaintenanceAnnouncement:
    """
    Announce deployments / maintenance mode on the website. Reasons for this:

    - 'seamless' deploy is not always possible, as some tasks (reloading config,
      rebuilding cache) are executed only if required and are only partially
      automated
    - to inform users, display a full-screen overlay (once) and a
      flash-notification for authenticated users.

    Steps:
    - the mangement command 'set_next_maintenance' writes the time of the next
      deploy into the file: envs/NEXT_DEPLOY (now plus timeout)
    - this command is called from the fabfile, after which the fabfile sleeps
      for the defined timeout
    - the context processor checks for above mentioned file, which is also
      cached to prevent file io.
    - for each user, a session key is set, making sure that the overlay is shown
      only once
    """

    # Cache timeout to re-read file with next maintenance time in seconds
    file_read_timeout = 60
    cache_key = 'next_maintenance'
    session_key = 'saw_deploy_warning'

    def __init__(self, request):
        self.request = request
        self.overlay = {}
        next_maintenance = self.get_next_maintenance()

        if next_maintenance and now() > next_maintenance:
            self.flush_maintenance_time()
        elif next_maintenance:
            self.set_display_deploy_warning(next_maintenance)
            self.set_maintenance_overlay(next_maintenance)

    def get_next_maintenance(self) -> Union[datetime, None]:
        """
        Check if maintenance is planned and return the datetime
        """
        if self.request.user and self.request.user.is_authenticated():
            # maybe: block editing depending on this variable as well.
            next_maintenance = cache.get(key=self.cache_key)
            if next_maintenance is None and isfile(settings.NEXT_MAINTENANCE):
                with open(settings.NEXT_MAINTENANCE) as f:
                    next_maintenance = f.read()
                    cache.set(
                        key=self.cache_key,
                        value=next_maintenance,
                        timeout=self.file_read_timeout
                    )

            if next_maintenance:
                with contextlib.suppress(ValueError):
                    return parse_datetime(next_maintenance)

        return None

    def flush_maintenance_time(self):
        """
        Flush file and unset cache
        """
        with open(settings.NEXT_MAINTENANCE, 'w') as f:
            f.flush()

        cache.set(
            key=self.cache_key,
            value='',
            timeout=self.file_read_timeout
        )

    def set_display_deploy_warning(self, next_maintenance_time: datetime) -> None:
        """
        For all requests: set the django message, displayed as 'flash' on the
        website.
        """
        messages.add_message(
            request=self.request,
            level=messages.WARNING,
            message=self.get_short_maintenance_text(next_maintenance_time),
            extra_tags='safe'
        )

    def set_maintenance_overlay(self, next_maintenance_time: datetime) -> None:
        """
        Once per maintenance window and user: show an overlay that the user must
        actively dismiss once.
        """
        saw_deploy_time = self.request.session.get(self.session_key, '')
        try:
            saw_deploy_time = parse_datetime(saw_deploy_time)
        except ValueError:
            saw_deploy_time = None

        if not saw_deploy_time or saw_deploy_time < now():
            self.request.session[self.session_key] = \
                next_maintenance_time.isoformat()
            text = self.get_full_maintenance_text(next_maintenance_time)
            self.overlay.update({'maintenance_warn_overlay': text})

    @staticmethod
    def get_full_maintenance_text(next_maintenance_time: datetime) -> str:
        return _('Caution: Maintenance will start soon ({}), this page will '
                 'then be unavailable for a couple of minutes.<br>'
                 'If you are working on a questionnaire, please make sure to '
                 'save your work!'.format(naturaltime(next_maintenance_time)))

    @staticmethod
    def get_short_maintenance_text(next_maintenance_time: datetime) -> str:
        return _('Maintenance starts in {}'.format(
            naturaltime(next_maintenance_time)
        ))
