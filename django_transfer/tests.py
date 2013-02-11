import os
import json
import tempfile
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.core.exceptions import ImproperlyConfigured


MULTIPART = 'multipart/form-data'


class ServerTestCase(TestCase):
    transfer_server = None
    old_settings = {}

    def setUp(self):
        self.old_settings = {
            'TRANSFER_SERVER': settings.TRANSFER_SERVER,
            'DEBUG': settings.DEBUG,
        }
        settings.TRANSFER_SERVER = self.transfer_server
        settings.DEBUG = False

    def tearDown(self):
        for name, value in self.old_settings.items():
            setattr(settings, name, value)

    def get_client(self):
        return Client()


class DownloadTestCase(ServerTestCase):
    def test_download(self):
        "Download test case for Apache / Lighttpd."
        r = self.get_client().get('/download')
        # Make sure the correct header is returned.
        self.assertIn(self.header_name, r.headers)
        # Ensure no data is returned.
        self.assertTrue(len(r.content), 0)
        # Make sure the returned file path exists on disk.
        self.assertTrue(os.path.exists(r.headers[self.header_name]))

    def test_download_debug(self):
        "Download test case for DEBUG == True."
        debug, settings.DEBUG = settings.DEBUG, True
        try:
            r = self.get_client().get('/download')
            # Ensure we receive the file content
            self.assertEqual(int(r.content), os.getpid())
        finally:
            settings.DEBUG = debug


class ApacheTestCase(DownloadTestCase):
    transfer_server = 'apache'
    header_name = 'X-SendFile'


class LighttpdTestCase(DownloadTestCase):
    transfer_server = 'lighttpd'
    header_name = 'X-SendFile'


class NginxTestCase(ServerTestCase):
    transfer_server = 'nginx'
    header_name = 'X-Accel-Redirect'

    def setUp(self):
        super(NginxTestCase, self).setUp()
        settings.TRANSFER_MAPPINGS = {
            '/tmp': '/downloads',
        }

    def tearDown(self):
        super(NginxTestCase, self).tearDown()
        delattr(settings, 'TRANSFER_MAPPINGS')

    def test_download(self):
        "Download test case for Nginx."
        r = self.get_client().get('/download')
        # Make sure the correct header is returned.
        self.assertIn(self.header_name, r.headers)
        # Ensure no data is returned.
        self.assertTrue(len(r.content), 0)
        # Nginx does not deal with absolute paths.
        self.assertTrue(r.headers[self.header_name].startswith('/downloads'))
        self.assertTrue(os.path.exists(os.path.join('/tmp',
                        os.path.basename(r.headers[self.header_name]))))

    def test_download_no_mappings(self):
        "Download test case for Nginx without mappings."
        # Remove the mappings.
        try:
            delattr(settings, 'TRANSFER_MAPPINGS')
        except AttributeError:
            pass
        # Without mappings, and server type nginx, we should see an
        # ImproperlyConfigured exception
        self.assertRaises(ImproperlyConfigured,
                          self.get_client().get, '/download')

    def test_upload_file(self):
        "Upload test case with real files."
        fd, t = tempfile.mkstemp()
        os.write(fd, str(os.getpid()))
        os.close(fd)
        data = {
            'file': file(t, 'r'),
        }
        r = self.get_client().post('/upload', data, content_type=MULTIPART)
        r = json.loads(r.content)
        self.assertIn('file', r)

    def test_upload_proxy(self):
        data = {
            'file[name]': '',
        }
        r = self.get_client().post('/upload', data, content_type=MULTIPART)
        r = json.loads(r.content)
        self.assertIn('file', r)
