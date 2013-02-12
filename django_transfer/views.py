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
    uploads = {}
    if request.method == 'POST':
        for name, file in request.FILES.items():
            uploads[name] = {
                'path': file.name,
                'size': file.size,
                'content-type': file.content_type,
                'data': file.read(),
            }
    response = HttpResponse(json.dumps(uploads), content_type='application/json')
    return response
