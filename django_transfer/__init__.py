from __future__ import unicode_literals

import os
import shutil
import mimetypes

from six.moves.urllib.parse import quote

from django.conf import settings
try:
    from django.http import StreamingHttpResponse
except:
    from django.http import HttpResponse as StreamingHttpResponse
from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ImproperlyConfigured
try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object


SERVER_APACHE = 'apache'
SERVER_NGINX = 'nginx'
SERVER_LIGHTTPD = 'lighttpd'

SERVER_HEADERS = {
    SERVER_APACHE: 'X-SendFile',
    SERVER_NGINX: 'X-Accel-Redirect',
    SERVER_LIGHTTPD: 'X-SendFile',
}

# Default to POST method only. Can be overridden in settings.
UPLOAD_METHODS = settings.TRANSFER_UPLOAD_METHODS or ['POST']


def get_server_name():
    try:
        return settings.TRANSFER_SERVER
    except AttributeError:
        raise ImproperlyConfigured('Please specify settings.TRANSFER_SERVER')


def get_header_name():
    # Allow user to customize.
    try:
        return settings.TRANSFER_HEADER
    except AttributeError:
        pass
    # Otherwise the header depends on the configured server type.
    server_name = get_server_name()
    try:
        return SERVER_HEADERS[server_name]
    except KeyError:
        raise ImproperlyConfigured('Invalid server name "%s" for '
                                   'settings.TRANSFER_SERVER' % server_name)


def is_enabled():
    if not hasattr(settings, 'ENABLE_TRANSFER'):
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


class TransferHttpResponse(StreamingHttpResponse):
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
            content = open(path, 'rb')
        super(TransferHttpResponse, self).__init__(content, status=status,
                                                   content_type=content_type)
        if enabled:
            # Now that the superclass is initialized, we can add our header.
            self[get_header_name()] = get_header_value(path)


class ProxyUploadedFile(UploadedFile):
    def __init__(self, path, name, content_type, size):
        self.path = path
        super(ProxyUploadedFile, self).__init__(open(path, 'rb'), name, content_type, size)

    def move(self, dst):
        "Closes then moves the file to dst."
        self.close()
        shutil.move(self.path, dst)


class TransferMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.method not in UPLOAD_METHODS:
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
            field, bracket, attr = name.partition('[')
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
                data = []
                try:
                    fields = enumerate(zip(request.POST.pop('%s[filename]' % field), request.POST.pop('%s[path]' % field)))
                except KeyError:
                    raise Exception('Missing required field "%s", please '
                                    'configure mod_upload properly')
                # Get optional fields. If these are missing, we will try to
                # determine the value from the temporary file.
                try:
                    content_types = dict(enumerate(request.POST.pop('%s[content_type]' % field)))
                except KeyError:
                    content_types = {}
                try:
                    sizes = dict(enumerate(request.POST.pop('%s[size]' % field)))
                except KeyError:
                    sizes = {}
                # Iterating over possible multiple files
                for i, (name, temp) in fields:
                    content_type = content_types[i] if i in content_types else mimetypes.guess_type(name)[0]
                    size = int(sizes[i]) if i in sizes else os.path.getsize(temp)
                    data.append(ProxyUploadedFile(temp, name, content_type, size))
                # Now add a new UploadedFile object so that the web application
                # can handle these "files" that were uploaded in the same
                # fashion as a regular file upload.
                if not data:
                    continue
                request.FILES.setlist(field, data)
            # We are done modifying these objects, make them immutable once
            # again.
            request.POST._mutable, request.FILES._mutable = False, False
