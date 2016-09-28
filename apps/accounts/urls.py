"""
This module contains the URL routing patterns for the :mod:`accounts`
app.
"""
from django.conf import settings
from django.conf.urls import patterns, url
from django_cas_ng import views as cas_views

from .views import LoginView, ProfileView, QuestionnaireStatusListView, \
    PublicQuestionnaireListView, UserDetailView

urlpatterns = patterns(
    '',
    url(r'^search/$', 'accounts.views.user_search', name='user_search'),
    url(r'^update/$', 'accounts.views.user_update', name='user_update'),
    url(r'^user/(?P<pk>\d+)/$', UserDetailView.as_view(), name='user_details'),
    url(r'^questionnaires/$',
        ProfileView.as_view(),
        name='account_questionnaires'
        ),
    url(r'^questionnaires/status/(?P<user_id>\d+)/$',
        PublicQuestionnaireListView.as_view(),
        name='questionnaires_public_list'
        ),
    url(r'^questionnaires/status/$',
        QuestionnaireStatusListView.as_view(),
        name='questionnaires_status_list'
        ),
)
if hasattr(settings, 'USE_NEW_WOCAT_AUTHENTICATION') and settings.USE_NEW_WOCAT_AUTHENTICATION:
    urlpatterns += patterns(
        '',
        url(r'^login/$', cas_views.login, name='login'),
        url(r'^logout/$', cas_views.logout, name='logout'),
    )
else:
    urlpatterns += patterns(
        '',
        url(r'^login/$', LoginView.as_view(), name='login'),
        url(r'^logout/$', 'accounts.views.logout', name='logout'),
    )
