from django.contrib import sitemaps
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render


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
            'unccd:home',
            'technologies:home',
            'approaches:home',
            'login',
        ]

    def location(self, item):
        return reverse_lazy(item)


# Use this for the urls.
static_sitemap = {
    'static': StaticViewSitemap,
}
