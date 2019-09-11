#!/usr/bin/env python

import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(HERE, 'README.md')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.md')).read()


setup(
    name='django-geostore',
    version=open(os.path.join(HERE, 'geostore', 'VERSION.md')).read().strip(),
    include_package_data=True,
    author="Makina Corpus",
    author_email="terralego-pypi@makina-corpus.com",
    description='Django geographic store and vector tile generation',
    long_description=README + '\n\n' + CHANGES,
    description_content_type="text/markdown",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url='https://github.com/Terralego/django-geostore.git',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        'django>=2.1,<3.0', # wait for restframework-gis, 0.14 doesnt support django 3.0
        'djangorestframework>=3.8',
        "djangorestframework-gis>=0.14",
        "drf-yasg>=1.9",
        "packaging", # wait for drf-yasg fix
        "deepmerge",
        "requests>=2.19",
        "mercantile>=1.0",
        "psycopg2>=2.7",
        "Fiona>=1.7",
        "Pillow>=5.3.0",
        "jsonschema>=3.0",
    ],
    extras_require={
        'dev': [
            'factory-boy',
            'flake8',
            'coverage',
        ]
    }
)
