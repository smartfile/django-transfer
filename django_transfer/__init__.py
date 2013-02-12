import os
import mimetypes

from urllib import quote

from django.http import HttpResponse
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ImproperlyConfigured


SERVER_APACHE = 'apache'
SERVER_NGINX = 'nginx'
SERVER_LIGHTTPD = 'lighttpd'

SERVER_HEADERS = {
    SERVER_APACHE: 'X-SendFile',
    SERVER_NGINX: 'X-Accel-Redirect',
    SERVER_LIGHTTPD: 'X-SendFile',
}


def get_server_name():
    try:
        return settings.TRANSFER_SERVER
    except AttributeError:
        raise ImproperlyConfigured('Please specify settings.TRANSFER_SERVER')


def get_header_name():
    try:
        server_name = get_server_name()
    except KeyError:
        raise ImproperlyConfigured('Invalid server name "%s" for '
                                   'settings.TRANSFER_SERVER' % server_name)
    return SERVER_HEADERS[server_name]


def get_header_value(path):
    if get_server_name() == SERVER_NGINX:
        try:
            mappings = settings.TRANSFER_MAPPINGS
        except AttributeError:
            raise ImproperlyConfigured('Please specify settings.TRANSFER_MAPPINGS')
        found = False
        for root, location in mappings.items():
            if path.startswith(root):
                found = True
                path = os.path.relpath(path, root).strip('/')
                path = os.path.join(location, path)
                break
        if not found:
            raise ImproperlyConfigured('Cannot map path "%s"' % path)
    # Can't use non-ASCII chars in headers.
    return quote(path.encode('utf-8'))


class TransferHttpResponse(HttpResponse):
    def __init__(self, path, mimetype=None, status=None,
                 content_type=None):
        if mimetype:
            content_type = mimetype
        if content_type is None:
            content_type = mimetypes.guess_type(path)[0]
        if not settings.DEBUG:
            content = ''
        else:
            content = file(path, 'r')
        super(TransferHttpResponse, self).__init__(content,  status=status,
                                                   content_type=content_type)
        if not settings.DEBUG:
            self[get_header_name()] = get_header_value(path)


class ProxyUploadedFile(UploadedFile):
    def __init__(self, path, name, content_type, size):
        super(ProxyUploadedFile, self).__init__(file(path, 'r'), name, content_type, size)


class TransferMiddleware(object):
    def process_request(self, request):
        if request.method != 'POST':
            return
        # Find uploads in request.POST and copy them to request.FILES.
        for name in request.POST.keys():
            n, ignored = name.split('[', 1)
