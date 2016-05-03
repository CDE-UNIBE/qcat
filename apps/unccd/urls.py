from django.conf.urls import url, patterns
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(
        url=reverse_lazy('wocat:home'), permanent=False
    ), name='home'),
    url(r'^view/(?P<identifier>[^/]+)/$', 'unccd.views.questionnaire_details',
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        'unccd.views.questionnaire_view_step',
        name='questionnaire_view_step'),
    url(r'^edit/new/$', 'unccd.views.questionnaire_new',
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>[^/]+)/$', 'unccd.views.questionnaire_new',
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        'unccd.views.questionnaire_new_step', name='questionnaire_new_step'),
    url(r'^list/$', 'unccd.views.questionnaire_list',
        name='questionnaire_list'),
    url(r'^list_partial/$', 'unccd.views.questionnaire_list_partial',
        name='questionnaire_list_partial'),
    url(r'^import/$', 'unccd.views.unccd_data_import', name='data_import'),
)
