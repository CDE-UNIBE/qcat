from django.conf.urls import url
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from questionnaire import views

from . import views as unccd_views


urlpatterns = [
    url(r'^$',
        RedirectView.as_view(url=reverse_lazy('wocat:home'), permanent=False),
        name='home'),
    url(r'^view/(?P<identifier>[^/]+)/$',
        views.QuestionnaireView.as_view(url_namespace=__package__),
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        unccd_views.questionnaire_view_step,
        name='questionnaire_view_step'),
    url(r'^edit/new/$',
        views.QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>[^/]+)/$',
        views.QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        views.QuestionnaireStepView.as_view(url_namespace=__package__),
        name='questionnaire_new_step'),
    url(r'^import/$',
        unccd_views.unccd_data_import,
        name='data_import'),
]
