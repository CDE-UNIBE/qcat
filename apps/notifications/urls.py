from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$',
        views.LogListTemplateView.as_view(),
        name='notification_list'
        ),
    url(r'^partial/$',
        views.LogListView.as_view(),
        name='notification_partial_list'
        ),
    url(r'^read/$',
        views.ReadLogUpdateView.as_view(),
        name='notification_read'
        ),
    url(r'^read/all/$',
        views.LogAllReadView.as_view(),
        name='notification_all_read'
        ),
    url(r'^inform-compiler/$',
        views.LogInformationUpdateCreateView.as_view(),
        name='notification_inform_compiler'
    ),
    url(r'^new-notifications/$',
        views.LogCountView.as_view(),
        name='notification_new_count'
        ),
    url(r'^questionnaire-logs/$',
        views.LogQuestionnairesListView.as_view(),
        name='notification_questionnaire_logs'),
    url(r'^preferences/(?P<token>\d+:[\w_-]+)/$',
        views.SignedLogSubscriptionPreferencesView.as_view(),
        name='signed_notification_preferences'),
    url(r'^preferences/$',
        views.LogSubscriptionPreferencesView.as_view(),
        name='notification_preferences'),
)
