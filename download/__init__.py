import os
import urllib
import mimetypes
from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ImproperlyConfigured
from django_download.archive import ZipStream


HEADERS = {
    'apache': ('X-SendFile: %(filename)s', ),
    'nginx': ('X-Accel-Redirect: %(base)s%/(filename)s',
              'X-Accel-Charset: %(encoding)s'),
}

# These won't change, get them now:
# TODO: raise configuration exceptions at run-time, who cares if
# we are not properly configured if the functions are not used?
OFFLOAD_METHOD = getattr(settings, 'DOWNLOAD_METHOD', '').lower()
if OFFLOAD_METHOD not in HEADERS:
    raise ImproperlyConfigured('Configure DOWNLOAD_METHOD to "apache" or '
                               '"nginx" before using `offload()`.')
OFFLOAD_HEADERS = HEADERS[OFFLOAD_METHOD]
OFFLOAD_ROOTS = getattr(settings, 'DOWNLOAD_OFFLOAD_ROOTS', (, ))
if OFFLOAD_METHOD == 'nginx' and not OFFLOAD_ROOTS:
   raise ImproperlyConfigured('You must set OFFLOAD_ROOTS when using'
                              'nginx as the OFFLOAD_METHOD.')
OFFLOAD_ROOTS = map(os.path.abspath, OFFLOAD_ROOTS)
OFFLOAD_GUESS = getattr(settings, 'OFFLOAD_GUESS', True)
COMBINE_PREPARE = getattr(settings, 'COMBINE_PREPARE', True)
COMBINE_PREPARE_ROOT = getattr(settings, 'COMBINE_PREPARE_ROOT', None)
if COMBINE_PREPARE and not COMBINE_PREPARE_ROOT:
    raise ImproperlyConfigured('You must set COMBINE_ROOT when using'
                               'COMBINE_PREPARE')


def add_headers(response, headers):
    for name, value in headers:
        response[name] = value


class FilenameWrapper(object):
    "A simple file-like object that has name and filename attributes."
    def __init__(self, name, stream):
       self.name = self.filename = name
       self.stream = stream

    def __getattr__(self, name):
        return getattr(self.stream, name)


def offload(f, headers={}, guess=OFFLOAD_GUESS):
    response = HttpResponse()
    if isinstance(f, basestring):
        filename = f
    else:
        try:
            filename = getattr(f, name, getattr(f, 'filename'))
        except AttributeError:
            raise Exception('File-like object must have `name` or `filename` '
                            'attribute. Try FilenameWrapper.')
    header_parts = {}
    if OFFLOAD_METHOD == 'nginx':
        matched_base = None
        for base in OFFLOAD_ROOTS:
            if filename.startswith(base):
                matched_base, filename = base, os.path.relpath(base, filename)
                break
        if not matched_base:
            raise Exception('Path not within any configured OFFLOAD_ROOTS.')
        header_parts['base'] = os.path.normpath(matched_base) + '/'
        # I don't see how this will work, Django won't allow this.
        # TODO: find an encoding scheme that nginx supports and also results
        # in a header value Django can live with.
        header_parts['filename'] = filename.encode('utf8')
        header_parts['encoding'] = 'utf-8'
    elif OFFLOAD_METHOD == 'apache':
        header_parts['filename'] = urllib.quote(filename)
    for header in OFFLOAD_HEADERS:
        name, value = header.split(':', 1)
        response[name] = value % header_parts)
    if guess:
        type, enc = mimetypes.guess_type(filename)
        if type:
            response['Content-Type'] = type
    # Add user-supplied headers last (to override our own).
    add_headers(response, headers)
    return response


def combine(*files, headers=None, prepare=COMBINE_PREPARE):
    if prepare is None:
        prepare = getattr(settings, 'DOWNLOAD_PREPARE', False)
    if prepare:
        f = ZipFile(*files)
        f.close()
        # Use offload to send the archive to the client.
        response = offload(f)
    else:
        f = ZipStream(*files)
        # Django will send this directly. The ZipStream is a generator that
        # will create the zip file one chunk at a time.
        response = HttpResponse(f)
    # Add user-supplied headers last (to override our own).
    add_headers(response, headers)
    return response

