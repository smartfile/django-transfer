A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

This is a simple Django application that encapsulates some methods for
sending files to an HTTP client.

Why
---

Why is this needed? First of all, Django is not well-suited for serving
up static files. You are well served by offloading this task to a server
that is, Apache and Nginx are two that come to mind.

Also, sometimes you want to do something fancy like allow a user to
download multiple files at once.

Usage
-----

In all cases, you can pass a file-like object or a path. If you pass a file-
like object, it MUST have a `name` or `filename` attribute. In the case of
`offload()` that attribute MUST return the full path of the file. A file path
will always work. For the `combine()` function, the `name` or `filename`
attribute is used to name the file within the zip archive, therefore it can
be a relative path or name (need not be valid).

A convenience wrapper `FilenameWrapper` is provided to allow you to use non-
compliant file-like objects. You can use it to wrap the file-like object as
follows::

    from django_download import FilenameWrapper

    def download_view(request):
        f = StringIO()
        f = FilenameWrapper('foobar.png', f)
        ...

The mime type will be guessed for you if you don't provide it. This is, this
is done using the `mimetypes.guess_type()` function. The mime type guessing is
another reason the file-like object must provide a file name.

*Offloading*

You can offload the sending of a file to your webserver using the `offload()`
function. This function will send a header to the server informing it that
the response to the client should consist of a file's contents. This allows
you to perform access checks in Django while actually sending the file via
you web server::

    from django_download import download

    def download_view(request):
        return download.offload(f,
               headers={ 'Content-Disposition': 'attachment;' })

This function works with Apache and Nginx using the X-SendFile and
X-Accel-Redirect headers respectively. For Apache, you must have
installed and configured mod_xsendfile.

https://tn123.org/mod_xsendfile/

For Nginx you must have configured the path as outlined in the Nginx
documentation.

http://wiki.nginx.org/XSendfile

*Combining*

If you want to combine multiple files into a single download (zipfile)
you can do so using the `combine()` function::

    from django_download import download

    def download_view(request):
        return download.combine(f1, f2,
                         headers={ 'Content-Disposition': 'attachment' })

This function will stream the archive to the client. Therefore, no Content-
Length header is provided. If you wish to build the archive on the server
before sending it to the client (so that the browser can estimate download
time) you can do so by setting the `DOWNLOAD_ARCHIVE_PREPARE` setting to True
or by sending the `prepare=True` keyword argument to `combine()`::

    from django_download import download

    def download_view(request):
        return download.combine(f1, f2, prepare=True)

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

Configuration
-------------

If you are using Apache or Nginx, you will need to configure some settings
to allow the offload() method to function.


.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
