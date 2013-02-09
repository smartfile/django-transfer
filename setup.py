#!/bin/env python

import os
from distutils.core import setup

name = 'django-transfer'
version = '0.1'
release = '1'
versrel = version + '-' + release
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
download_url = 'https://github.com/downloads/smartfile' \
               '/' + name + '/' + name + '-' + versrel + '.tar.gz'
long_description = file(readme).read()

setup(
    name = name,
    version = versrel,
    description = 'A django application that offloads file transfers to a downstream proxy.',
    long_description = long_description,
    author = 'Ben Timby',
    author_email = 'btimby@gmail.com',
    maintainer = 'Ben Timby',
    maintainer_email = 'btimby@gmail.com',
    url = 'http://github.com/smartfile/' + name + '/',
    download_url = download_url,
    license = 'MIT',
    requires = [],
    packages = [
        "django_transfer",
    ],
    classifiers = (
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
