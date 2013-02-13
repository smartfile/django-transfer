import os
import json
import tempfile

from django.http import HttpResponse

from django_transfer import TransferHttpResponse


def download(request):
    fd, t = tempfile.mkstemp()
    os.write(fd, str(os.getpid()))
    os.close(fd)
    return TransferHttpResponse(t)


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
