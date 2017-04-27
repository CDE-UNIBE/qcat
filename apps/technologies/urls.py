from django.conf.urls import url, patterns
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from questionnaire.views import QuestionnaireEditView, QuestionnaireStepView, \
    QuestionnaireMapView, QuestionnaireAddModule, \
    QuestionnaireCheckModulesView, QuestionnaireView, \
    QuestionnaireLinkSearchView

urlpatterns = patterns(
    '',
    # The 'home' route points to the list
    url(r'^view/(?P<identifier>[^/]+)/$',
        QuestionnaireView.as_view(url_namespace=__package__),
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>[^/]+)/map/$',
        QuestionnaireMapView.as_view(url_namespace=__package__),
        name='questionnaire_view_map'),
    url(r'^view/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        'technologies.views.questionnaire_view_step',
        name='questionnaire_view_step'),
    url(r'^edit/new/$', QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>[^/]+)/$', QuestionnaireEditView.as_view(url_namespace=__package__),
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>[^/]+)/(?P<step>\w+)/$',
        QuestionnaireStepView.as_view(url_namespace=__package__),
        name='questionnaire_new_step'),
    url(r'^search/links/$', QuestionnaireLinkSearchView.as_view(
        configuration_code=__package__), name='questionnaire_link_search'),
    url(r'^add_module/$',
        login_required(
            TemplateView.as_view(template_name="technologies/add_module.html")),
        name='add_module'),
    url(r'^add_module_action/$',
        QuestionnaireAddModule.as_view(url_namespace=__package__),
        name='add_module_action'),
    url(r'^check_modules/$', QuestionnaireCheckModulesView.as_view(),
        name='check_modules')
)
