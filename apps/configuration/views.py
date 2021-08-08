# -*- coding: utf-8 -*-
import contextlib
import importlib.util
from pathlib import Path

from braces.views import LoginRequiredMixin, SuperuserRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import RedirectView, TemplateView
from django.utils.translation import ugettext_lazy as _

from .cache import delete_configuration_cache
from .editions.base import Edition
from .models import Configuration


@login_required
def delete_caches(request):
    """
    Delete all the caches.

    Args:
        ``request`` (django.http.HttpRequest): The request object.

    Returns:
        ``HttpResponse``. A rendered Http Response (redirected to the
        search admin home page).
    """
    if request.user.is_superuser is not True:
        raise PermissionDenied()

    for configuration in Configuration.objects.all():
        delete_configuration_cache(configuration)

    messages.success(request, 'Caches deleted.')

    return redirect('search:admin')


class BuildAllCachesView(LoginRequiredMixin, SuperuserRequiredMixin,
                         RedirectView):
    """
    Build cache for all questionnaires.
    """
    url = reverse_lazy('search:admin')
    permanent = False
    login_url = reverse_lazy('login')

    def get(self, request, *args, **kwargs):
        self.build_caches(request)
        return super().get(request, *args, **kwargs)

    def build_caches(self, request):
        """
        Build the cache for all active configurations.

        """
        call_command('build_config_caches')

        messages.success(request, _(u"Built configuration caches."))


class EditionNotesView(TemplateView):
    """
    'Release notes' for configurations.

    """
    template_name = 'configuration/edition_notes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editions'] = self.get_editions()
        return context

    @staticmethod
    def get_editions():
        """
        Filter configurations with at least one edition. Only editions that are 'applied' to the
        database should be listed on the release notes page.
        """
        configurations = Configuration.objects.exclude(edition=2015)
        for configuration in configurations:
            yield configuration.get_edition()


