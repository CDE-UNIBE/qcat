import contextlib
import logging
from os.path import join, isfile

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.utils.translation import get_language

from wkhtmltopdf.views import PDFTemplateView, PDFTemplateResponse

from configuration.cache import get_configuration
from questionnaire.models import Questionnaire
from questionnaire.utils import get_query_status_filter, \
    get_questionnaire_data_in_single_language
from summary.renderers import TechnologyFullSummaryRenderer, \
    ApproachesFullSummaryRenderer

logger = logging.getLogger(__name__)


class SummaryPDFCreateView(PDFTemplateView):
    """
    Put the questionnaire data to the context and return the rendered pdf.
    """
    # Activate this as soon as frontend is finished.
    # response_class = CachedPDFTemplateResponse

    # Refactor this when more than one summary type is available.
    summary_type = 'full'
    base_template_path = 'summary/'
    http_method_names = ['get']
    render_classes = {
        'technologies': {'full': TechnologyFullSummaryRenderer},
        'approaches': {'full': ApproachesFullSummaryRenderer}
    }
    footer_template = '{}layout/footer.html'.format(base_template_path)
    # see: http://wkhtmltopdf.org/usage/wkhtmltopdf.txt
    cmd_options = {
        'margin-top': '1cm',
        'margin-bottom': '1cm',
    }

    def get(self, request, *args, **kwargs):
        self.questionnaire = self.get_object(questionnaire_id=self.kwargs['id'])
        self.code = self.questionnaire.configurations.filter(
            active=True
        ).first().code
        self.config = get_configuration(configuration_code=self.code)
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        template = self.request.GET.get('template', self.code)
        return '{}/layout/{}.html'.format(self.base_template_path, template)

    def get_filename(self) -> str:
        """
        The filename is specific enough to be used as 'pseudo cache-key' in the
        CachedPDFTemplateResponse.
        """
        return 'wocat-{identifier}-{summary_type}-summary-{update}.pdf'.format(
            summary_type=self.summary_type,
            identifier=self.questionnaire.id,
            update=self.questionnaire.updated.strftime('%Y-%m-%d-%H:%m')
        )

    def get_object(self, questionnaire_id: int) -> Questionnaire:
        """
        Get questionnaire and check status / permissions.
        """
        status_filter = get_query_status_filter(self.request)
        status_filter &= Q(id=questionnaire_id)
        obj = Questionnaire.with_status.not_deleted().filter(
            Q(id=questionnaire_id), status_filter
        ).distinct()
        if not obj.exists() or obj.count() != 1:
            raise Http404
        return obj.first()

    def get_summary_data(self, **data):
        """
        Load summary config according to configuration.
        """
        try:
            renderer = self.render_classes[self.config.keyword][self.summary_type]
        except KeyError:
            raise Exception('Summary not configured.')
        return renderer(
            config=self.config, questionnaire=self.questionnaire,
            base_url=self.request.build_absolute_uri('/'), **data
        ).data

    def get_prepared_data(self, questionnaire: Questionnaire) -> dict:
        """
        Load the prepared JSON for given object in the current language.
        """
        data = get_questionnaire_data_in_single_language(
            questionnaire_data=questionnaire.data,
            locale=get_language(),
            original_locale=questionnaire.original_locale
        )
        return self.get_summary_data(**data)

    def get_footer_context(self) -> dict:
        """
        Provide variables used in the footer template.
        """
        questionnaire_names = self.config.get_questionnaire_name(
            self.questionnaire.data
        )
        name = questionnaire_names.get(get_language(), questionnaire_names['en'])
        if len(name) > 50:
            name = '{}...'.format(name[:47])
        return {
            'footer_name': name,
            'footer_config': self.code.title()
        }

    def get_context_data(self, **kwargs):
        """
        Dump json to the context, the markup for the pdf is created with a js
        library in the frontend.
        """
        context = super().get_context_data(**kwargs)
        context['block'] = self.get_prepared_data(self.questionnaire)
        context.update(self.get_footer_context())
        return context


class CachedPDFTemplateResponse(PDFTemplateResponse):
    """
    Creating the pdf includes two resource-heavy processes:
    - extracting the json to markup (frontend)
    - call to wkhtmltopdf (backend)

    Therefore, the content is created only once per filename (which should
    distinguish between new questionnaire edits). This only works with
    reasonably precise file names!
    """

    @property
    def rendered_content(self):
        file_path = join(settings.SUMMARY_PDF_PATH, self.filename)
        if isfile(file_path):
            with contextlib.suppress(Exception) as e:
                # Catch any kind of error and log it. PDF is created from
                # scratch again.
                logger.warning(
                    "Couldn't open pdf summary from disk: {}".format(e))
                return open(file_path, 'rb').read()

        content = super().rendered_content
        with contextlib.suppress(Exception) as e:
            # Again, intentionally catch any kind of exception.
            logger.warning(
                "Couldn't write pdf summary from disk: {}".format(e))
            open(file_path, 'wb').write(content)
        return content
