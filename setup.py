#!/bin/env python

import os
from setuptools import setup

name = 'django-transfer'
version = '0.3'
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
with open(readme) as readme_file:
    long_description = readme_file.read()

setup(
    name = name,
    version = version,
    description = 'A django application that offloads file transfers to a downstream proxy.',
    long_description = long_description,
    author = 'SmartFile',
    author_email = 'team@smartfile.com',
    maintainer = 'Travis Cunningham',
    maintainer_email = 'tcunningham@smartfile.com',
    url = 'http://github.com/smartfile/' + name + '/',
    license = 'MIT',
    install_requires = [
        "six>=1.9.0",
    ],
    packages = [
        "django_transfer",
    ],
    classifiers = (
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
