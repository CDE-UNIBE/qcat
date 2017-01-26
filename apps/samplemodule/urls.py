from django.conf.urls import url, patterns

from questionnaire.views import QuestionnaireEditView, GenericQuestionnaireStepView

urlpatterns = patterns(
    '',
    url(r'^view/(?P<identifier>[^/]+)/$',
        'samplemodule.views.questionnaire_details',
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        'samplemodule.views.questionnaire_view_step',
        name='questionnaire_view_step'),
    url(r'^edit/new/$', QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>[^/]+)/$',
        QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        GenericQuestionnaireStepView.as_view(url_namespace=__package__),
        name='questionnaire_new_step'),
)
