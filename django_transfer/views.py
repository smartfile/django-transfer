import os
import tempfile
from django_transfer.offload import TransferHttpResponse


def download(request):
    fd, t = tempfile.mkstemp()
    os.write(os.getpid())
    os.close(fd)
    return TransferHttpResponse(t)


def upload(request):
    uploads = {}
    if request.method == 'POST':
        for name, file in request.FILES.items():
            uploads[name] = {
                'size': file.size,
                'content-type': file.content_type,
            }
    response = HttpResponse()
    pprint.pprint(uploads, response)
    return response
