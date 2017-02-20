from django.conf.urls import patterns, url, include
from rest_framework_swagger.views import get_swagger_view
from api.views import APIRoot


urlpatterns = patterns(
    '',
    url(r'^v1/', include('api.urls.v1', namespace='v1')),
    url(r'^v2/', include('api.urls.v2', namespace='v2')),
    url(r'^docs/', get_swagger_view(title='QCAT API'), name='api-docs'),
    url(r'^$', APIRoot.as_view(), name='api-root'),
)

