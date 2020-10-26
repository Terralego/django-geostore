Installation
============

Requirements
------------

DATABASE
^^^^^^^^

Minimum configuration :
 * Python 3.6+
 * PostgreSQL 10
 * PostGIS 2.4

And if you want to use Routing :

 * PgRouting 2.5 + django-geostore-routing

Recommended configuration :
 * Python 3.8
 * PostgreSQL 11
 * PostGIS 2.5

And if you want to use Routing :

 * PgRouting 2.6 + django-geostore-routing

Your final django project should use django.contrib.gis.backend.postgis as default DATABASE backend


USING docker image :

https://hub.docker.com/r/postgis
or
https://hub.docker.com/r/pgrouting

SYSTEM REQUIREMENTS
^^^^^^^^^^^^^^^^^^^

these are debian packages required

- libpq-dev   (psycopg2)
- gettext     (translations)
- binutils    (django.contrib.gis)
- libproj-dev (django.contrib.gis)
- gdal-bin    (django.contrib.gis)

recommended

- postgresql-client (if you want to use ./manage.py dbshell command)

With pip
--------

From Pypi:

::

    pip install django-geostore

From Github:

::

    pip install -e https://github.com/Terralego/django-geostore.git@master#egg=geostore

With git
--------

::

    git clone https://github.com/Terralego/django-geostore.git
    cd django-geostore
    python setup.py install
