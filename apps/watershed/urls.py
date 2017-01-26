from django.conf.urls import url, patterns

from questionnaire.views import QuestionnaireEditView, \
    GenericQuestionnaireStepView, GenericQuestionnaireMapView, QuestionnaireView

urlpatterns = patterns(
    '',
    # The 'home' route points to the list
    url(r'^$', 'watershed.views.questionnaire_list', name='home'),
    url(r'^view/(?P<identifier>[^/]+)/$',
        QuestionnaireView.as_view(url_namespace=__package__),
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>[^/]+)/map/$',
        GenericQuestionnaireMapView.as_view(url_namespace=__package__),
        name='questionnaire_view_map'),
    url(r'^view/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        'watershed.views.questionnaire_view_step',
        name='questionnaire_view_step'),
    url(r'^edit/new/$',
        QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>[^/]+)/$',
        QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        GenericQuestionnaireStepView.as_view(url_namespace=__package__),
        name='questionnaire_new_step'),
    url(r'^list/$', 'watershed.views.questionnaire_list',
        name='questionnaire_list'),
    url(r'^list_partial/$', 'watershed.views.questionnaire_list_partial',
        name='questionnaire_list_partial'),
)
