from django.conf.urls import url, patterns

from questionnaire.views import QuestionnaireEditView, QuestionnaireStepView, \
    QuestionnaireMapView

urlpatterns = patterns(
    '',
    # The 'home' route points to the list
    url(r'^$', 'cca.views.questionnaire_list', name='home'),
    url(r'^view/(?P<identifier>[^/]+)/$',
        'cca.views.questionnaire_details',
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>[^/]+)/map/$',
        QuestionnaireMapView.as_view(url_namespace=__package__),
        name='questionnaire_view_map'),
    url(r'^view/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        'cca.views.questionnaire_view_step',
        name='questionnaire_view_step'),
    url(r'^edit/new/$', QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>[^/]+)/$', QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        QuestionnaireStepView.as_view(url_namespace=__package__),
        name='questionnaire_new_step'),
    url(r'^search/links/$', 'cca.views.questionnaire_link_search',
        name='questionnaire_link_search'),
    url(r'^list/$', 'cca.views.questionnaire_list',
        name='questionnaire_list'),
    url(r'^list_partial/$', 'cca.views.questionnaire_list_partial',
        name='questionnaire_list_partial'),
)
