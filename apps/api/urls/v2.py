from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from questionnaire.api import views as questionnaire_views
from configuration.api import views as configuration_views
from api import views as api_views

urlpatterns = {
    url(r'^questionnaires/$',
        questionnaire_views.QuestionnaireListView.as_view(),
        name='questionnaires-api-list'
        ),

    # url(r'^questionnaires/(?P<identifier>[^/]+)/$',
    url(r'^questionnaires/(?P<identifier>(?!mydata)[^/]+)/$',
        questionnaire_views.ConfiguredQuestionnaireDetailView.as_view(),
        name='questionnaires-api-detail',
        ),

    url(r'^auth/login/$',
        api_views.ObtainAuthToken.as_view(),
        name="api-token-auth"),

    url(r'^questionnaires/(?P<configuration>[^/]+)/(?P<edition>[^/]+)/create/$',
        questionnaire_views.QuestionnaireCreateNew.as_view(),
        name='questionnaires-api-create',
        ),

    url(r'^questionnaires/(?P<configuration>[^/]+)/(?P<edition>[^/]+)/(?P<identifier>(?!create)[^/]+)/$',
        questionnaire_views.QuestionnaireEdit.as_view(),
        name='questionnaires-api-edit',
        ),

    url(r'^questionnaires/mydata/$',
        questionnaire_views.QuestionnaireMyData.as_view(),
        name='questionnaires-api-mydata',
        ),

    url(r'^image/upload/$',
        questionnaire_views.QuestionnaireImageUpload.as_view(),
        name="questionnaires-api-image-upload"),

    url(r'^configuration/(?P<code>[^/]+)/(?P<edition>[^/]+)/$',
        configuration_views.ConfigurationStructureView.as_view(),
        name='api-configuration-structure',
        ),

    url(r'^configuration/$',
        configuration_views.ConfigurationView.as_view(),
        name='configuration-api-list',
        ),

    url(r'^configuration/(?P<code>[^/]+)/$',
        configuration_views.ConfigurationEditionView.as_view(),
        name='configuration-edition-api-list',
        ),
}

urlpatterns = format_suffix_patterns(urlpatterns)
