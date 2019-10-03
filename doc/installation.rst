Installation
============

Requirements
------------

DATABASE
^^^^^^^^

Minimum configuration :
 * Postgresql 10
 * PostGIS 2.4
 * PgRouting 2.5

Recommended configuration :
 * Postgresql 11
 * PostGIS 2.5
 * PgRouting 2.6

Your final django project should use django.contrib.gis.backend.postgis as default DATABASE backend


USING docker image :

Prebuilt docker image builded by makinacorpus

https://cloud.docker.com/u/makinacorpus/repository/docker/makinacorpus/pgrouting/general

SYSTEM REQUIREMENTS
^^^^^^^^^^^^^^^^^^^

For django
""""""""""

libpq-dev
gettext


For geodjango
"""""""""""""

gdal-bin
binutils
libproj-dev


With pip
--------

From Pypi:

::

    pip install xxxxxxxxxx-xxxxxxxxxxxx

From Github:

::

    pip install -e https://github.com/Terralego/django-geostore.git@master#egg=geostore

With git
--------

::

    git clone https://github.com/Terralego/django-geostore.git
    cd django-geostore
    python setup.py install
