from django.conf.urls import url, patterns
from django.views.generic import TemplateView

from .views import HomeView

urlpatterns = patterns(
    '',
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^help/questionnaire/$', TemplateView.as_view(
        template_name='wocat/help/questionnaire_introduction.html'),
        name='help_questionnaire_introduction'),
    url(r'^help/review/$', TemplateView.as_view(
        template_name='wocat/help/review_process.html'),
        name='help_review_process'),
    url(r'^faq/$', TemplateView.as_view(
        template_name='wocat/faq.html'),
        name='faq'),
    url(r'^add/$', TemplateView.as_view(
        template_name='wocat/add.html'),
        name='add'),
    url(r'^list/$', 'wocat.views.questionnaire_list',
        name='questionnaire_list'),
    url(r'^list_partial/$', 'wocat.views.questionnaire_list_partial',
        name='questionnaire_list_partial'),
)
