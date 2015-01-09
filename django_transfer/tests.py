from __future__ import unicode_literals

import os
import json
from django.test import TestCase
from django.test.client import Client
from django.core.exceptions import ImproperlyConfigured

from django_transfer import settings
from django_transfer import SERVER_HEADERS
from django_transfer.views import make_tempfile


MULTIPART = 'multipart/form-data'


# Note: I tried using the override_settings() decorator and the
# TestCase.with_settings() method to manage per-test settings. This however
# DOES NOT WORK. The reason is that if settings has already been imported,
# it is untouched. These methods ONLY affect settings imported from the
# point of their calling onward. This is no help to us since our module
# imports beforehand. Instead I simply pull settings in from our module
# and manage changing the settings on THAT.


class Settings(object):
    "Context manager that overrides settings, then restores them."
    class Missing(object):
        "A sentinal for a missing setting."
        pass

    def __init__(self, settings, **kwargs):
        self.restore = {}
        self.settings = settings
        for name, value in kwargs.items():
            self.restore[name] = getattr(settings, name, Settings.Missing)
            if value is Settings.Missing:
                if hasattr(settings, name):
                    delattr(settings, name)
            else:
                setattr(settings, name, value)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        for name, value in self.restore.items():
            if value is Settings.Missing:
                if hasattr(self.settings, name):
                    delattr(self.settings, name)
            else:
                setattr(self.settings, name, value)


class ServerTestCase(TestCase):
    transfer_server = None

    def setUp(self):
        super(ServerTestCase, self).setUp()
        self.header_name = SERVER_HEADERS.get(self.transfer_server)

    def assertIn(self, value, iterable):
        self.assertTrue(value in iterable, '%s did not occur in %s' % (value,
                        iterable))

    def getClient(self):
        return Client()


class DownloadTestCase(object):
    def test_download(self):
        "Download test case for Apache / Lighttpd."
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server):
            r = self.getClient().get('/download/')
        # Make sure the correct header is returned.
        self.assertIn(self.header_name, r)
        # Ensure no data is returned.
        content_len = sum(len(chunk) for chunk in r.streaming_content)
        self.assertEqual(content_len, 0)
        # Make sure the returned file path exists on disk.
        self.assertTrue(os.path.exists(r[self.header_name]))

    def test_download_debug(self):
        "Download test case for DEBUG == True."
        with Settings(settings, DEBUG=True):
            r = self.getClient().get('/download/')
        # Ensure we receive the file content
        content = ''.join(chunk.decode() for chunk in r.streaming_content)
        self.assertEqual(int(content), os.getpid())


class UploadTestCase(object):
    def test_upload_file(self):
        "Upload test case with real file."
        t = make_tempfile()
        with open(t, 'rb') as file_obj:
            data = {
                'file': file_obj,
            }
            with Settings(settings, DEBUG=False,
                          TRANSFER_SERVER=self.transfer_server):
                r = self.getClient().post('/upload/', data)
        r = json.loads(r.content.decode())
        self.assertEqual(os.getpid(), int(r['files']['file']['data']))


class NoneServerTestCase(UploadTestCase, ServerTestCase):
    def test_download(self):
        "Download test case when disabled."
        with Settings(settings, DEBUG=False, TRANSFER_SERVER=Settings.Missing):
            r = self.getClient().get('/download/')
        # Ensure we receive the file content
        self.assertEqual(int(''.join(chunk.decode() for chunk in r.streaming_content)), os.getpid())


class BadServerTestCase(UploadTestCase, ServerTestCase):
    transfer_server = 'foobar'

    def test_download(self):
        "Download test case when server is invalid."
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server):
            self.assertRaises(ImproperlyConfigured, self.getClient().get,
                              '/download/')


class ApacheTestCase(DownloadTestCase, UploadTestCase, ServerTestCase):
    transfer_server = 'apache'


class NginxTestCase(DownloadTestCase, UploadTestCase, ServerTestCase):
    transfer_server = 'nginx'

    def test_download(self):
        "Download test case for Nginx."
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server,
                      TRANSFER_MAPPINGS={'/tmp': '/downloads'}):
            r = self.getClient().get('/download/')
        # Make sure the correct header is returned.
        self.assertIn(self.header_name, r)
        # Ensure no data is returned.
        content_len = sum(len(chunk) for chunk in r.streaming_content)
        self.assertEqual(content_len, 0)
        # Nginx does not deal with absolute paths. Verify the mapping was done
        # properly.
        self.assertTrue(r[self.header_name].startswith('/downloads'))
        self.assertTrue(os.path.exists(os.path.join('/tmp',
                        os.path.basename(r[self.header_name]))))

    def test_download_no_mappings(self):
        "Download test case for Nginx without mappings."
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server,
                      TRANSFER_MAPPINGS=Settings.Missing):
            # Without mappings, and server type nginx, we should see an
            # ImproperlyConfigured exception
            self.assertRaises(ImproperlyConfigured,
                              self.getClient().get, '/download/')

    def test_upload_field(self):
        "Upload test with regular fields."
        data = {
            'test': 'value',
            'test[foobar]': 'value',
        }
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server):
            r = self.getClient().post('/upload/', data)
        r = json.loads(r.content.decode())
        self.assertEqual(data, r['fields'])

    def test_upload_proxy(self):
        "Upload test case with proxied file."
        t = make_tempfile()
        data = {
            'file[filename]': 'foobar.png',
            'file[path]': t,
        }
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server):
            r = self.getClient().post('/upload/', data)
        r = json.loads(r.content.decode())
        self.assertEqual(os.getpid(), int(r['files']['file']['data']))

    def test_upload_proxy_optional(self):
        "Upload test case with proxied file."
        t = make_tempfile()
        data = {
            'file[filename]': 'foobar.png',
            'file[path]': t,
            'file[content_type]': 'image/png',
            'file[size]': os.path.getsize(t),
        }
        with Settings(settings, DEBUG=False,
                      TRANSFER_SERVER=self.transfer_server):
            r = self.getClient().post('/upload/', data)
        r = json.loads(r.content.decode())
        self.assertEqual(os.getpid(), int(r['files']['file']['data']))
