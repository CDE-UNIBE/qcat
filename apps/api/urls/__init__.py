from django.conf.urls import url, include
from api.views import APIRoot, SwaggerSchemaView


urlpatterns = [
    url(r'^v1/', include(('api.urls.v1','v1'), namespace='v1')),
    url(r'^v2/', include(('api.urls.v2','v2'), namespace='v2')),
    url(r'^docs/', SwaggerSchemaView.as_view(), name='api-docs'),
    url(r'^$', APIRoot.as_view(), name='api-root'),
]
