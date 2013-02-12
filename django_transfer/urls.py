try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url, handler500, handler404


urlpatterns = patterns(
    '',
    url(r'^download/.*$', 'django_transfer.views.download', name='download'),
    url(r'^upload/$', 'django_transfer.views.upload', name='upload'),
)
