"""
This module contains the URL routing patterns for the :mod:`accounts`
app.
"""
from django.conf.urls import patterns, url

from .views import LoginView


urlpatterns = patterns(
    '',
    url(r'^login$', LoginView.as_view(), name='login'),
    url(r'^logout$', 'accounts.views.logout', name='logout'),
    url(r'^search$', 'accounts.views.user_search', name='user_search'),
    url(r'^update$', 'accounts.views.user_update', name='user_update'),
    url(r'^user/(?P<id>\d+)$', 'accounts.views.details', name='user_details'),
    url(r'^moderation$', 'accounts.views.moderation',
        name='account_moderation'),
    url(r'^(?P<user_id>[0-9]+)/questionnaires$',
        'accounts.views.questionnaires', name='account_questionnaires'),
)
