.. figure:: https://travis-ci.org/smartfile/django-transfer.png
   :alt: Travis CI Status
   :target: https://travis-ci.org/smartfile/django-transfer

A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

The Django project recommends serving static files from a different web
server than the one executing the web application. This is easy to implement
when the static files are web assets. These resources can be served to any
anonymous user and can easily be cached. However, in some cases, an
application must control access to files, or even allow users to upload
files. In these cases, there is a need to tightly control the process,
which runs contrary to the Django project's recommendations.

Luckily, there are a few tools available that allow removing downloads
and even uploads from the application server, while still allowing it
to control the process. This Django application is meant to help
integrate with such tools, so that your web application can hand off
file transfers to a downstream proxy server, which is better equipped
to handle this task, freeing up the application server for the heavy
lifting.

django-transfer integrates with:

- `mod_xsendfile`_ for Apache
- `X-Accel-Redirect`_ for Nginx
- `X-SendFile`_ header in Lighttpd
- `mod_upload`_ for Nginx

The first three of the above allow the web application to emit a header
instructing the content server to transfer a file to the HTTP client.
This way, the web app still receives the download request, performs any
checks required, and sends a header instead of the actual file contents.

The last, `mod_upload`_ does something similar, but for file UPLOADS.
mod_upload will receive files POSTed to the server and save them off
to temporary files. It will then forward the request to the web
application, replacing the file bodies with paths to the temporary files
containing them.

`mod_upload`_ is better than simply buffering the upload because the file
bodies are NEVER handled by the application server. In fact, if you can
write the temporary files to a holding area that exists on the same volume
as their final location, a simple move is all that is required to finish
the upload. In fact, the ``ProxyUploadedFile`` class (contained in
``request.FILES`` has a convenience ``move()`` method.

Downloading
-----------

django-transfer provides an HttpResponse subclass that handles downloads
triggered via response header. The actual header and format are handled by
this class. TransferHttpResponse accepts a path, and handles the transfer.
When ``settings.DEBUG == True`` the path is sent directly to the client,
this allows the Django development server to function as normal without
changing your application code.

The timeline of events for a download looks like the following.

1. A client initiates a download (GET request).
2. The downstream server forwards the request to Django.
3. Django application authenticates the user and does other necessary
   processing.
4. Django application returns a ``TransferHttpResponse``.
5. The ``TransferHttpResponse`` emits a header instructing the downstream
   server to transfer a file to the client.

First you must configure django-transfer and let it know the details
about your downstream server.

*Server Types*

::

    TRANSFER_SERVER = 'apache'  # or 'nginx' or 'lighttpd'

You can change the server type and TransferHttpResponse will use the
correct header(s) for the configured server.

*Nginx Mappings*

Nginx has support for the X-Accel-Redirect header built in. However, it
does not accept arbitrary paths for transfer. Nginx requires that you
configure internal locations, and return a path relative to one of those.

For example, if you configure:

::

    location /downloads {
        internal;
        alias /mnt/shared/downloads;
    }

When nginx receives the header ``X-Accel-Redirect: /downloads/foo/bar.png``
it will transfer ``'/mnt/shared/downloads/foo/bar.png'`` to the client.

django-transfer needs to know about such locations. You can inform it of
them by configuring the mappings.

::

    TRANSFER_MAPPINGS = {
        '/mnt/shared/downloads': '/downloads',
    }

Once the mapping is configured, you can use absolute paths, which will
be converted to the locations required by nginx. If you later switch to
a different server (apache or lighttpd), these absolute paths will continue
to function without changing your code. Similarly, when ``settings.DEBUG ==
True``, absolute paths will be required so that the development server can
send the file directly.

If you do not configure any mappings, and you are using server type
``'nginx'``, an ImproperlyConfigured exception will be raised. Mappings
are ignored when the server type is not ``'nginx'``.

*Apache Configuration*

Apache requires a module to be installed in order to use the X-Sendfile
header. Once installed, this module must be enabled, and you must define
the locations that allow downloads. Much like Nginx, Apache will not
serve arbitrary paths, only those specifically configured.

::

    XSendFile On
    XSendFilePath /mnt/shared/downloads

When apache receives the header ``X-SendFile: /mnt/shared/downloads/foo/bar.png``
It will transfer ``'/mnt/shared/downloads/foo/bar.png'`` to the client.
django-transfer will pass along absolute paths when the server type is
``'apache'``.

*Lighttpd Configuration*

TODO: I have never used lighttpd, but I know it supports this.

Uploading
---------

Uploads are handled using a similar (but reversed) process. Nginx
supports uploading with `mod_upload`_. This is not part of the default
server, so you must build nginx with support for uploading. If available,
the upload module will strip file contents from POST requests, save
them to temporary files and then forward those file names to your
application.

1. A client initiates an upload (POST reqest).
2. The downstream server saves any file(s) to a holding area.
3. The downstream server forwards the request (minus the file content) to
   Django.
4. Django does any processing that is necessary and returns a response.
5. The downstream server relays the response to the client.

To handle downstream uploads in the same way you handle regular file
uploads, you must install the ``TransferMiddleware``. This middleware
processes the ``request.POST`` data, identifying uploaded files and
creating new entries in ``request.FILES`` to represent them.

::

    MIDDLEWARE_CLASSES = (
        ...
        'django_transfer.TransferMiddleware',
        ...
    )

Nginx requires a bit of configuration to make this possible. Below is a
sample configuration.

::

    location /upload {
        upload_pass @application;

        # The path below must exist, so must subdirectories named 0-9
        # $ mkdir -p /mnt/shared/uploads/{0-9}
        upload_store /mnt/shared/uploads 1;
        upload_store_access user:r;

        # You can limit file size here...
        upload_max_file_size 0;

        # These are the MINIMUM fields required by django-transfer.
        # mod_upload will replace $upload_field_name with the name of the file
        # field. If there are multiple files, your web application will receive
        # a set of filename/paths for each.
        upload_set_form_field $upload_field_name[filename] "$upload_file_name";
        upload_set_form_field $upload_field_name[path] "$upload_tmp_path";

        # You can also pass along the following fields, otherwise
        # django-transfer will attempt to "figure out" these values on it's
        # own.
        upload_set_form_field $upload_field_name[content_type] "$upload_content_type";
        upload_aggregate_form_field $upload_field_name[size] "$upload_file_size";

        # If you want to receive non-file fields provide the following, note
        # that if nginx supports it, this can be a regular expression. If not
        # you can define allowed fields separately, by providing this argument
        # multiple times.
        upload_pass_form_field ".*";

        # If you want to receive querystring arguments...
        upload_pass_args on;
    }

    location / {
        # ... proxy-pass or FCGI directives here ...
        # This is where requests to URLs other than /upload go.
    }

    location @application {
        # ... proxy-pass or FCGI directives here ...
        # This is where to pass upload requests, most frequently, it will be
        # the same as the previous location.
    }

For more information on how to install and configure mod_upload, see the
following pages, I found them useful while implementing this.

http://www.grid.net.ru/nginx/upload.en.html
http://blog.joshsoftware.com/2010/10/20/uploading-multiple-files-with-nginx-upload-module-and-upload-progress-bar/
http://bclennox.com/extremely-large-file-uploads-with-nginx-passenger-rails-and-jquery

Your views can now handle regular or downstream uploads in the same fashion.

Development / Debugging
-----------------------

When ``settings.DEBUG == True``, ``TransferHttpResponse`` will transfer the
file directly which suitable for use with the Django development server.
The ``TransferMiddleware`` always supports regular file uploads, so it
will also function properly when ``settings.DEBUG == True``.

Non-ASCII File Names
--------------------

This library does nothing to help with non-ASCII filenames, however, a
quick note on this topic might save you some headache.

A common practice is to include a Content-Disposition header that
includes the file name. This breaks when the filename contains non-ASCII
characters (UTF-8 etc). Specifically, Django will raise an exception when
you try to set the header. The HTTP specification states that headers must
contain only ASCII.

The best workaround I have found for this is to include the file name in
the URL. It must be the last element of the URL. All browsers I know of
will use this file name in the "Save As" dialog. Since a URL can contain
any character, this works around the issue. To implement this, I
generally add a regular expression to urls.py that ignores the file name.
The file name is there only for the benefit of the browser, and is not
used by the Django view. Thus::

    url('^/download/.*', 'myapp.views.download'),

will allow an optional trailing file name for our purposes. You then must
ensure that any links to your download view include the file name, like so::

    http://myapp.com/download/desired_filename.png

When the user clicks that link and the application sends file contents, the
browser will obtain the file name from the URL. The browser may decide to
render or save the file. You can force the issue (saving vs. rendering) by
including a Content-Disposition header with the value "attachment;"
excluding the (unsafe) filename.

.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
.. _mod_xsendfile: https://tn123.org/mod_xsendfile/
.. _X-Accel-Redirect: http://wiki.nginx.org/XSendfile
.. _X-SendFile: http://redmine.lighttpd.net/projects/1/wiki/Docs_ModFastCGI#X-Sendfile
.. _mod_upload: http://wiki.nginx.org/HttpUploadModule



Compatability
-------------

+--------------------------------------------------+
| Python                                           |
+--------------------+-----+-----+-----+-----+-----+
|                    | 2.7 | 3.3 | 3.4 | 3.5 | 3.6 |
+====================+=====+=====+=====+=====+=====+
| Django      | 1.4  |  O  |  X  |  X  |  X  |  X  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.5  |  O  |  O  |  O  |  X  |  X  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.6  |  O  |  O  |  O  |  X  |  X  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.7  |  O  |  O  |  O  |  X  |  X  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.8  |  O  |  O  |  O  |  O  |  O  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.9  |  O  |  X  |  O  |  O  |  O  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.10 |  O  |  X  |  O  |  O  |  O  |
|             +------+-----+-----+-----+-----+-----+
|             | 1.11 |  O  |  X  |  O  |  O  |  O  |
+-------------+------+-----+-----+-----+-----+-----+
