#!/bin/env python

import os
from setuptools import setup

name = 'django-transfer'
version = '0.2'
release = '2'
versrel = version + '-' + release
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
with open(readme) as readme_file:
    long_description = readme_file.read()

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
