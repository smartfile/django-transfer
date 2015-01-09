from __future__ import unicode_literals

import os
import json
import tempfile

from django.http import HttpResponse
import six

from django_transfer import TransferHttpResponse


def make_tempfile():
    "Create a temp file, write our PID into it."
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        temp.write(six.text_type(os.getpid()))
        return temp.name


def download(request):
    return TransferHttpResponse(make_tempfile())


def upload(request):
    files, fields = {}, {}
    echo = {
        'files': files,
        'fields': fields,
    }
    if request.method == 'POST':
        for name, file in request.FILES.items():
            files[name] = {
                'path': file.name,
                'size': file.size,
                'content-type': file.content_type,
                'data': file.read().decode(),
            }
        for name, value in request.POST.items():
            fields[name] = value
    return HttpResponse(json.dumps(echo), content_type='application/json')
