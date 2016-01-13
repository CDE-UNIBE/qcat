"""
Class based views. This could also go into views.py, but this should help to
separate the varying code styles.
"""
from django.http import Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import formats
from django.utils.timezone import now
from django.utils.translation import get_language
from wkhtmltopdf.views import PDFTemplateView

from configuration.cache import get_configuration
from questionnaire.models import Questionnaire
from questionnaire.utils import get_questionnaire_data_in_single_language, \
    get_list_values, get_query_status_filter


class PDFDetailView(PDFTemplateView):
    """
    Return a pdf version of the print view for a given questionnaire.

    This view is mostly ported and adapted to a class based view from
    questionnaire.views.generic_questionnaire_details
    """
    # template_name = 'approaches/questionnaire/details.html'
    template_name = 'home.html'
    http_method_names = ['get', ]
    configuration_code = 'approaches'

    def get(self, request, *args, **kwargs):
        if not self.kwargs.get('identifier'):
            raise Http404()

        self.object = self.get_object()
        self.questionnaire_configuration = \
            self.get_questionnaire_configuration
        self.data = self.get_data()
        self.permissions = self.get_permissions()
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return get_object_or_404(Questionnaire, code=self.kwargs['identifier'])

    def get_filename(self):
        """The name of the pdf file"""
        return '{code}_{date}.pdf'.format(
            code=self.kwargs['identifier'],
            date=formats.date_format(now(), "SHORT_DATETIME_FORMAT")
        )

    @property
    def get_questionnaire_configuration(self):
        """
        :rtype: object of configuration.configuration.QuestionnaireConfiguration
        """
        return get_configuration(self.configuration_code)

    def get_data(self):
        return get_questionnaire_data_in_single_language(
            self.object.data, get_language()
        )

    def get_images(self):
        return self.questionnaire_configuration.get_image_data(
            self.data
        ).get('content', [])

    def get_review_config(self):
        if self.request.user.is_authenticated() and self.object.status != 4:
            # Show the review panel only if the user is logged in and if the
            # version shown is not active.
            return {
                'review_status': self.object.status,
                'csrf_token_value': get_token(self.request),
                'permissions': self.permissions,
            }
        else:
            return {}

    def get_sections(self):
        return self.questionnaire_configuration.get_details(
            data=self.data, permissions=self.permissions,
            review_config=self.get_review_config(),
            questionnaire_object=self.object
        )

    def get_identifier(self):
        return self.kwargs['identifier']

    def get_filter_configuration(self):
        return self.questionnaire_configuration.get_filter_configuration()

    @property
    def get_links_by_configuration(self):
        links_by_configuration = {}
        status_filter = get_query_status_filter(self.request)
        for linked in self.object.links.filter(status_filter):
            configuration = linked.configurations.first()
            if configuration is None:
                continue
            if configuration.code not in links_by_configuration:
                links_by_configuration[configuration.code] = [linked]
            else:
                # Add each questionnaire (by code) only once to avoid having
                # multiple (pending) versions of the same questionnaire
                # shown.
                found = False
                for link in links_by_configuration[configuration.code]:
                    if link.code == linked.code:
                        found = True
                if found is False:
                    links_by_configuration[configuration.code].append(linked)
        return links_by_configuration

    def get_links_display(self):
        link_display = {}
        for configuration, links in self.get_links_by_configuration.items():
            link_display[self.configuration] = get_list_values(
                configuration_code=self.configuration,
                questionnaire_objects=links,
                with_links=False
            )

    def get_permissions(self):
        return self.object.get_permissions(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = self.get_images()
        context['sections'] = self.get_sections()
        context['questionnaire_identifier'] = self.get_identifier()
        context['links'] = self.get_links_display()
        context['filter_configuration'] = self.get_filter_configuration()
        context['permissions'] = self.permissions
        context['view_mode'] = 'view',
        return context
