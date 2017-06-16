from __future__ import unicode_literals

try:
    from django.conf.urls import url

    def patterns(*args):
        return args

except ImportError:
    from django.conf.urls.defaults import patterns, url

from django_transfer.views import download, upload


urlpatterns = patterns(
    url(r'^download/.*$', download, name='download'),
    url(r'^upload/$', upload, name='upload'),
)
