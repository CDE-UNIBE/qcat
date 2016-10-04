from django.conf.urls import patterns, url

from .views import LogListTemplateView, LogListView, ReadLogUpdateView, \
    LogCountView, LogQuestionnairesListView

urlpatterns = patterns(
    '',
    url(r'^$',
        LogListTemplateView.as_view(),
        name='notification_list'
        ),
    url(r'^partial/$',
        LogListView.as_view(),
        name='notification_partial_list'
        ),
    url(r'^read/$',
        ReadLogUpdateView.as_view(),
        name='notification_read'
        ),
    url(r'^new-notifications/$',
        LogCountView.as_view(),
        name='notification_new_count'
        ),
    url(r'^questionnaire-logs/$',
        LogQuestionnairesListView.as_view(),
        name='notification_questionnaire_logs')
)
