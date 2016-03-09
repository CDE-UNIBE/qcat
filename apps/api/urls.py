from django.conf.urls import patterns, url, include
from rest_framework.urlpatterns import format_suffix_patterns

from questionnaire.api.views import QuestionnaireListView

from .views import APIRoot, ObtainNoteAuthTokenView

api_root_patterns = [
    url(r'^$', APIRoot.as_view(), name='api-root'),
]

urlpatterns = patterns(
    '',
    url(r'^questionnaires/$',
        QuestionnaireListView.as_view(),
        name='questionnaires-api-list'
        ),
    url(r'^auth-token/$', ObtainNoteAuthTokenView.as_view(),
        name='obtain-api-token'),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)

# Workaround: the api root must not be in the API docs. Only namespaces can
# be excluded - so a namespace is created for this single view.
urlpatterns = urlpatterns + patterns(
    '',
    url(r'^$', include((api_root_patterns, 'api', 'api-root'))),
)

urlpatterns = format_suffix_patterns(urlpatterns)
