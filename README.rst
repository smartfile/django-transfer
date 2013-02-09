A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

This is a simple Django application that encapsulates some methods for
sending and receiving files. This application helps with using
`mod_xsendfile`_ (Apache), `X-Accel-Redirect`_ (nginx), `X-SendFile`_ 
(lighttpd) and `mod_upload`_ (nginx).

If your web application needs to allow users to upload or download files
this will help you accelerate these tasks while retaining control over
the process.

Downloading
-----------

Downloads are handled by the downstream web server (or proxy). However,
the process is still controlled by the Django web application.

1. A client initiates a download (GET request).
2. The downstream server forwards the request to Django.
3. Django authenticates the user, or does other necessary processing.
4. Django returns a TransferResponse.
5. The TransferResponse instructs the downstream server to send the file.

First you must configure django-transfer and let it know the details
about your downstream server.

*Server type.*

::

    TRANSFER_SERVER = 'apache'  # or 'nginx' or 'lighttpd'

You can always change the server type, and your code should continue
to work.

*Mappings.*

Apache and Lighttpd both accept absolute paths. Nowever, nginx requires
that you configure internal locations, and return a path relative to
one of those.

For example, if you configure:

::

    location /downloads {
        internal;
        alias /mnt/shared/downloads;
    }


When you serve the path '/downloads/foo/bar.png', nginx will transfer
'/mnt/shared/downloads/foo/bar.png' to the client. You can configure
your locations so that django-transfer can convert an absolute path
to one that nginx can use to serve the file.

::

    TRANSFER_MAPPINGS = (
        ('/downloads', '/mnt/shared/downloads'),
    )

If you don't configure any mappings, django-transfer will pass your
path unmodified. If you configure mappings, it will attempt the
conversion if the conversion fails, an ImproperlyConfigured
exception will be raised. Mappings are ignored when the server type
is not 'nginx'. You can change the server type, and everything
should just work. With the proper mappings, absolute paths are
handled properly, and for non-nginx servers, absolute paths are
used directly.

Uploading
---------

Uploads are handled using a similar (but reversed) process. Nginx
supports uploading with `mod_upload`_. This is not part of the default
server, so you must build nginx with support for uploading. If available
the upload module will strip file contents from POST requests, save
them to temporary files, and then forward those file names to your
application.

1. A client initials an upload (POST reqest).
2. The downstream server saves any file(s) to a holding area.
3. The downstream server forwards the request (minus the file content) to
Django.
4. Django does any processing that is necessary, and returns a response.
5. The downstream server relays the response to the client.

To handle downstream uploads in the same way you handle regular file
uploads, you must install the TransferMiddleware. This middleware
processes the request.POST data, identifying uploaded files and
creates new entries in request.FILES to represent them.

::

    MIDDLEWARE_CLASSES = (
        ...
        'django_transfer.middleware.TransferMiddleware',
        ...
    )

You views can now handle regular or downstream uploads in the same fashion.

Development / Debugging
-----------------------

When settings.DEBUG is True, TransferResponse will transfer the file directly
this is suitable for use with the Django development server. The
TransferUploadHandler always supports regular file uploads, so it will
also function properly when settings.DEBUG is True.

Non-ASCII File Names
--------------------

This library does nothing to help with non-ASCII filenames, however, a
quick note on this topic might save you some headache.

A common practice is to include a Content-Disposition header that
includes the file name. This breaks when the filename contains non-ASCII
characters (UTF8 etc). Specifically, Django will raise an exception when
you try to set the header. HTTP specification states that headers must
contain only ASCII.

The best workaroud I have found for this is to include the file name in
the URL. It must be the last element of the URL. All browser I know of
will use this file name in the "Save As" dialog. Since a URL can contain
any character, this works around the issue. To implement this, I
generally add a regular expression to urls.py that ignores the file name.
The file name is there only for the benefit of the browser, and is not
used by the Django view. Thus::

    url('/download/.*', 'myapp.views.download'),

Will allow an optional trailing file name for our purposes. You then must
ensure that any links to your download view include the file name, like so::

    http://myapp.com/download/desired_filename.png

When the user clicks that link, if you send file contents, and the browser
decides to save them rather than render them, the filename will be
populated in the "Save As" dialog. You can force the issue (saving vs.
rendering) by including a Content-Disposition header with the value
"attachment;" excluding the (unsafe) filename.

.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
.. _Read more: http://www.smartfile.com/open-source.html
.. _mod_xsendfile: https://tn123.org/mod_xsendfile/
.. _X-Accel-Redirect: http://wiki.nginx.org/XSendfile
.. _X-SendFile: http://redmine.lighttpd.net/projects/1/wiki/Docs_ModFastCGI#X-Sendfile
.. _mod_upload: http://wiki.nginx.org/HttpUploadModule
