"""
This module contains the URL routing patterns for the :mod:`accounts`
app.
"""
from django.conf.urls import patterns, url

from .views import LoginView, ProfileView, QuestionnaireStatusListView, \
    PublicQuestionnaireListView, UserDetailView

urlpatterns = patterns(
    '',
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', 'accounts.views.logout', name='logout'),
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
