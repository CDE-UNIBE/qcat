from django.contrib import sitemaps
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render
from django.views.generic import TemplateView



def home(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')


class StaticViewSitemap(sitemaps.Sitemap):
    """
    Until a better solution is required: just use a static sitemap.
    """
    def items(self):
        return [
            'wocat:home',
            'technologies:home',
            'approaches:home',
            'login',
        ]

    def location(self, item):
        return reverse_lazy(item)


class ServiceWorkerView(TemplateView):
    """
    The scope of the service worker must be the project root. Deliver the js
    here
    """
    content_type='application/javascript'
    template_name = 'js/serviceWorker.js'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['template_url'] = static('assets/html/offline.html')
        # Increment version to cache a new version of the file.
        # This could be automated by using a hash - but this is too expensive
        # for this purpose.
        ctx['version'] = 1
        # Cache the logo as well.
        ctx['img_url'] = static('/static/assets/img/wocat_logo.svg')
        return ctx

# Use this for the urls.
static_sitemap = {
    'static': StaticViewSitemap,
}
