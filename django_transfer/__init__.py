import os
import shutil
import mimetypes

from urllib import quote

from django.conf import settings
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
    server_name = get_server_name()
    try:
        return SERVER_HEADERS[server_name]
    except KeyError:
        raise ImproperlyConfigured('Invalid server name "%s" for '
                                   'settings.TRANSFER_SERVER' % server_name)


def is_enabled():
    if settings.DEBUG:
        return False
    if getattr(settings, 'TRANSFER_SERVER', None) is None:
        return False
    return True


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
    return quote(path.encode('utf-8'))


class TransferHttpResponse(HttpResponse):
    def __init__(self, path, mimetype=None, status=None,
                 content_type=None):
        if mimetype:
            content_type = mimetype
        if content_type is None:
            content_type = mimetypes.guess_type(path)[0]
        enabled = is_enabled()
        if enabled:
            # Don't send content, we will instead send a header.
            content = ''
        else:
            # Fall back to sending file contents via Django HttpResponse.
            content = file(path, 'r')
        super(TransferHttpResponse, self).__init__(content, status=status,
                                                   content_type=content_type)
        if enabled:
            # Now that the superclass is initialized, we can add our header.
            self[get_header_name()] = get_header_value(path)


class ProxyUploadedFile(UploadedFile):
    def __init__(self, path, name, content_type, size):
        self.path = path
        super(ProxyUploadedFile, self).__init__(file(path, 'r'), name, content_type, size)

    def move(self, dst):
        "Closes then moves the file to dst."
        self.close()
        shutil.move(self.path, dst)


class TransferMiddleware(object):
    def process_request(self, request):
        if request.method != 'POST':
            return
        if not is_enabled():
            return
        if get_server_name() != SERVER_NGINX:
            return
        # Find uploads in request.POST and copy them to request.FILES. Such
        # fields are expected to be named as:
        # __original_field_name__[__attribute__]
        # We will build a unique list of the __original_field_name__'s we find
        # that contain a valid __attribute__ name.
        fields = set()
        for name in request.POST.keys():
            field, attr = name.split('[', 1)
            if attr in ('filename]', 'path]', 'size]', 'content_type]'):
                fields.add(field)
        # If we found any field names that match the expected naming scheme, we
        # can now loop through the names, and try to extract the attributes.
        # The original fields will be pop()ed off request.POST, to clean up.
        if fields:
            # We will be modifying these objects, so make them mutable.
            request.POST._mutable, request.FILES._mutable = True, True
            for field in fields:
                # Get required fields. If these are missing, we will fail.
                try:
                    name = request.POST.pop('%s[filename]' % field)[0]
                    temp = request.POST.pop('%s[path]' % field)[0]
                except KeyError:
                    raise Exception('Missing required field "%s", please '
                                    'configure mod_upload properly')
                # Get optional fields. If these are missing, we will try to
                # determine the value from the temporary file.
                try:
                    content_type = int(
                        request.POST.pop('%s[content_type]' % field))[0]
                except (KeyError, ValueError):
                    content_type = mimetypes.guess_type(name)[0]
                try:
                    size = int(request.POST.pop('%s[size]' % field))[0]
                except (KeyError, ValueError):
                    size = os.path.getsize(temp)
                # Now add a new UploadedFile object so that the web application
                # can handle these "files" that were uploaded in the same
                # fashion as a regular file upload.
                request.FILES[field] = ProxyUploadedFile(temp, name,
                                                         content_type, size)
            # We are done modifying these objects, make them immutable once
            # again.
            request.POST._mutable, request.FILES._mutable = False, False
