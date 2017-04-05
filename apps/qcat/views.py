import contextlib
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib import sitemaps
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from requests.exceptions import RequestException

from questionnaire.models import Questionnaire, QuestionnaireMembership

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')


class StaticViewSitemap(sitemaps.Sitemap):
    """
    Until a better solution is required: just use a static sitemap.
    """
    def items(self):
        return [
            'wocat:home',
            'technologies:home',
            'approaches:home',
            'login',
        ]

    def location(self, item):
        return reverse_lazy(item)


# Use this for the urls.
static_sitemap = {
    'static': StaticViewSitemap,
}


class FactsTeaserView(TemplateView):
    """
    Display some relevant numbers.
    This is built with the idea that the date-range can be edited by the user.
    """
    http_method_names = ['get']
    template_name = 'qcat/templates/fact_sheet_teaser.html'
    start_date_offset_days = 90
    date_to = timezone.now()
    date_launch = '2016-08-01'
    piwik_date_format = '%Y-%m-%d'

    @property
    def date_from(self):
        return timezone.now() - timedelta(days=self.start_date_offset_days)

    @method_decorator(cache_page(60 * 60))
    def dispatch(self, request, *args, **kwargs):
        """
        This page will take some time to load - cache it.
        """
        return super().dispatch(request, *args, **kwargs)

    @property
    def piwik_api_url(self) -> str:
        return '{base_url}/?module=API&idSite={site_id}&' \
               'token_auth={auth_token}&format=JSON'.format(
            base_url=settings.PIWIK_URL.rstrip('/piwik.php'),
            site_id=settings.PIWIK_SITE_ID,
            auth_token=settings.PIWIK_AUTH_TOKEN
        )

    def get_questionnaire_facts(self):
        """
        Get data about questionnaires.
        """
        return {
            'questionnaires': Questionnaire.with_status.public().count(),
            'technologies': Questionnaire.with_status.public().filter(
                code__startswith='technologies'
            ).count(),
            'approaches': Questionnaire.with_status.public().filter(
                code__startswith='approaches'
            ).count(),
            'unccd': Questionnaire.with_status.public().filter(
                code__startswith='unccd'
            ).count(),
            'created': Questionnaire.with_status.not_deleted().filter(
                created__gte=self.date_from
            ).count(),
            'countries': len(set(Questionnaire.with_status.public().extra(
                select={'countries': "data->'qg_location'->0->'country'"}
            ).values_list('countries', flat=True)))
        }

    def get_user_facts(self):
        """
        Get data about users.
        """
        return {
            'compilers': QuestionnaireMembership.objects.filter(
                questionnaire__status=settings.QUESTIONNAIRE_PUBLIC,
                role='compiler'
            ).distinct('user').count(),
            'users': get_user_model().objects.all().count()
        }

    @staticmethod
    def log_piwik_error(url):
        logger.error('exception when querying to piwik: {}'.format(url))

    def get_piwik_facts(self) -> dict:
        """
        Get data from piwik.
        """
        def piwik_query(url):
            """
            Helper function to query Piwik and check for errors.
            """
            try:
                query = requests.get(url)
            except RequestException:
                self.log_piwik_error(url)
                return {}
            try:
                json_data = query.json()
            except AttributeError:
                self.log_piwik_error(url)
                return {}
            if isinstance(json_data, dict) and json_data.get('result') == 'error':
                self.log_piwik_error(url)
                return {}
            return json_data

        countries_url = '{piwik_api}&method=UserCountry.getCountry&' \
                        'period=range&date={start_date},{end_date}&' \
                        'filter_limit={filter_limit}'\
            .format(
                piwik_api=self.piwik_api_url,
                start_date=self.date_launch,
                end_date=self.date_to.strftime(self.piwik_date_format),
                filter_limit=-1,  # No limit
            )

        visits_url = '{piwik_api}&method=VisitsSummary.getVisits&' \
                     'period=range&date={start_date},{end_date}&' \
                     'filter_limit={filter_limit}' \
            .format(
                piwik_api=self.piwik_api_url,
                start_date=self.date_launch,
                end_date=self.date_to.strftime(self.piwik_date_format),
                filter_limit=-1,  # No limit
            )

        return {
            'piwik_countries': len(piwik_query(countries_url)),
            'piwik_visits': piwik_query(visits_url).get('value', 0)
        }

    def get_context_data(self, **kwargs) -> dict:
        """
        Combine all kinds of facts.
        """
        context = super().get_context_data(**kwargs)
        context['days'] = self.start_date_offset_days
        context.update(**self.get_questionnaire_facts())
        context.update(**self.get_user_facts())
        context.update(**self.get_piwik_facts())
        return context
