from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from .views import static_sitemap


urlpatterns = patterns(
    '',

    url(r'^$', 'qcat.views.home', name='home'),
    url(r'^about/$', 'qcat.views.about', name='about'),

    # View to change language
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': static_sitemap},
        name='django.contrib.sitemaps.views.sitemap')
)

# The following urls are created with the locale as prefix, eg.
# en/questionnaire
urlpatterns += i18n_patterns(
    '',
    url(r'^$', 'qcat.views.home', name='home'),
    url(r'^questionnaire/', include('questionnaire.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^wocat/', include('wocat.urls', namespace='wocat')),
    url(r'^wocat/technologies/', include('technologies.urls',
        namespace='technologies')),
    url(r'^wocat/approaches/', include('approaches.urls',
        namespace='approaches')),
    url(r'^unccd/', include('unccd.urls', namespace='unccd')),
    url(r'^search/', include('search.urls', namespace='search')),
    url(r'^api/v1/', include('api.urls')),
)

if settings.DEBUG:
    urlpatterns += i18n_patterns(
        '',
        url(r'^sample/', include('sample.urls', namespace='sample')),
        url(r'^samplemulti/', include('samplemulti.urls',
            namespace='samplemulti')),
        url(r'^404/', TemplateView.as_view(template_name='404.html')),
        url(r'^500/', TemplateView.as_view(template_name='500.html')),
        url(r'^503/', TemplateView.as_view(template_name='503.html')),
    ) + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
