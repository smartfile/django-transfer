import os
import json
import tempfile

from django.http import HttpResponse

from django_transfer import TransferHttpResponse


def make_tempfile():
    "Create a temp file, write our PID into it."
    fd, t = tempfile.mkstemp()
    try:
        os.write(fd, str(os.getpid()))
    finally:
        os.close(fd)
    return t


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
                'data': file.read(),
            }
        for name, value in request.POST.items():
            fields[name] = value
    return HttpResponse(json.dumps(echo), content_type='application/json')
