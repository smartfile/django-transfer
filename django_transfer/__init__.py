from django.http import HttpResponse
from django.core.files.uploadedfile import UploadedFile


class TransferHttpResponse(HttpResponse):
    pass


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
