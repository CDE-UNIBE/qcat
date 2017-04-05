from unittest.mock import sentinel, MagicMock, patch, mock_open, call

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404
from django.test import RequestFactory
from django.test import override_settings
from django.utils.timezone import now
from wkhtmltopdf.views import PDFTemplateResponse

from qcat.tests import TestCase
from summary.views import SummaryPDFCreateView, CachedPDFTemplateResponse


class QuestionnaireSummaryPDFCreateViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.base_view = SummaryPDFCreateView()
        self.base_url = reverse('questionnaire_summary', kwargs={'id': 1})
        self.request = self.factory.get(self.base_url)
        self.request.user = MagicMock()
        self.view = self.setup_view(self.base_view, self.request, id=1)
        self.view.code = 'sample'

    @patch.object(SummaryPDFCreateView, 'get_object')
    @patch.object(SummaryPDFCreateView, 'get_prepared_data')
    @patch('summary.views.get_configuration')
    def test_get(self, mock_get_configuration, mock_prepared_data, mock_object):
        mock_object.return_value = MagicMock()
        view = self.view.get(request=self.request)
        self.assertIsInstance(view, PDFTemplateResponse)

    @patch.object(SummaryPDFCreateView, 'get_prepared_data')
    def test_get_context_data(self, mock_data):
        self.view.questionnaire = MagicMock()
        self.view.code = 'sample'
        mock_data.return_value = sentinel.summary_data
        context = self.view.get_context_data()
        self.assertEqual(
            context['block'], sentinel.summary_data
        )

    def test_get_filename(self):
        this_moment = now()
        expected = 'wocat-id-en-full-summary-{}.pdf'.format(
            this_moment.strftime('%Y-%m-%d-%H:%m')
        )
        self.view.questionnaire = MagicMock(
            id='id', updated=this_moment
        )
        self.assertEqual(
            expected, self.view.get_filename()
        )

    @patch('summary.views.get_configuration')
    def test_get_summary_data(self, mock_config):
        renderer = MagicMock()
        base_view = SummaryPDFCreateView()
        base_view.code = 'code'
        base_view.summary_type = 'summary_type'
        base_view.render_classes = {'config_type': {'summary_type': renderer}}
        base_view.questionnaire = MagicMock()
        mock_config.keyword = 'config_type'
        base_view.config = mock_config
        view = self.setup_view(base_view, self.request, id=1)
        view.get_summary_data()
        renderer.assert_called_once_with(
            base_url='http://testserver/',
            config=mock_config,
            questionnaire=base_view.questionnaire
        )

    @patch('summary.views.get_query_status_filter')
    def test_get_object(self, mock_status_filter):
        mock_status_filter.return_value = Q()
        with self.assertRaises(Http404):
            self.view.get_object(questionnaire_id='1')
        mock_status_filter.assert_called_once_with(self.request)

    def test_get_template_names(self):
        self.view.code = 'bar'
        self.assertEqual(
            '{}/layout/bar.html'.format(self.view.base_template_path),
            self.view.get_template_names()
        )

    def test_get_custom_template_names(self):
        url = '{}?template=foo'.format(self.base_url)
        base_path = sentinel.base_path
        view = self.setup_view(self.base_view, self.factory.get(url), id=1)
        view.code = 'bar'
        view.base_template_path = base_path
        self.assertEqual(
            '{}/layout/foo.html'.format(base_path), view.get_template_names()
        )


class TestCachedPDFTemplateResponse(TestCase):

    def setUp(self):
        super().setUp()
        self.request = RequestFactory()
        self.obj = CachedPDFTemplateResponse(
            request=self.request, template=MagicMock()
        )
        self.obj.filename = 'foo'

    @patch('summary.views.isfile')
    def test_rendered_content_existing_file(self, mock_isfile):
        mock_isfile.return_value = True
        with patch('summary.views.open', mock_open(read_data='hit')):
            self.assertEqual(
                self.obj.rendered_content,
                'hit'
            )

    @patch('summary.views.isfile')
    @override_settings(SUMMARY_PDF_PATH = 'pdf_path')
    def test_rendered_content_creates_file(self, mock_isfile):
        mock_isfile.return_value = False
        with patch('summary.views.open') as open_mock:
            self.obj.rendered_content
            path = 'pdf_path/{}'.format(self.obj.filename)
            self.assertIn(call(path, 'wb'), open_mock._mock_mock_calls)
