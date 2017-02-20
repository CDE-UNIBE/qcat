from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from questionnaire.api import views

from ..views import ObtainNoteAuthTokenView

urlpatterns = patterns(
    '',
    url(r'^questionnaires/$',
        views.QuestionnaireListView.as_view(),
        name='questionnaires-api-list'
        ),
    url(r'^questionnaires/(?P<identifier>[^/]+)/$',
        views.QuestionnaireDetailView.as_view(),
        name='questionnaires-api-detail',
        ),
    url(r'^auth-token/$', ObtainNoteAuthTokenView.as_view(),
        name='obtain-api-token'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
