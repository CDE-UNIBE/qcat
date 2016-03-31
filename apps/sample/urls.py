from django.conf.urls import url, patterns

urlpatterns = patterns(
    '',
    url(r'^$', 'sample.views.home', name='home'),
    url(r'^view/(?P<identifier>\w+)/$', 'sample.views.questionnaire_details',
        name='questionnaire_details'),
    url(r'^view/(?P<identifier>\w+)/(?P<step>\w+)/$',
        'sample.views.questionnaire_view_step',
        name='questionnaire_view_step'),
    url(r'^edit/new/$', 'sample.views.questionnaire_new',
        name='questionnaire_new'),
    url(r'^edit/(?P<identifier>\w+)/$', 'sample.views.questionnaire_new',
        name='questionnaire_edit'),
    url(r'^edit/(?P<identifier>\w+)/(?P<step>\w+)/$',
        'sample.views.questionnaire_new_step', name='questionnaire_new_step'),
    url(r'^search/links/$', 'sample.views.questionnaire_link_search',
        name='questionnaire_link_search'),
    url(r'^list/$', 'sample.views.questionnaire_list',
        name='questionnaire_list'),
    url(r'^list_partial/$', 'sample.views.questionnaire_list_partial',
        name='questionnaire_list_partial'),
)
