[![Build Status](https://travis-ci.org/Terralego/django-geostore.svg?branch=master)](https://travis-ci.org/Terralego/django-geostore/)
[![codecov](https://codecov.io/gh/Terralego/django-geostore/branch/master/graph/badge.svg)](https://codecov.io/gh/Terralego/django-geostore)
[![Maintainability](https://api.codeclimate.com/v1/badges/b6119d8175fa6f5f5949/maintainability)](https://codeclimate.com/github/Terralego/django-geostore/maintainability)
[![Documentation Status](https://readthedocs.org/projects/django-geostore/badge/?version=latest)](https://django-geostore.readthedocs.io/en/latest/?badge=latest)

![Python Version](https://img.shields.io/badge/python-%3E%3D%203.6-blue.svg)
![Django Version](https://img.shields.io/badge/django-%3E%3D%202.2-blue.svg)

# django-geostore

Dynamic geographic datastore with Vector Tiles generation from PostGIS and json schema definition and validation.

## Functions

* Geographic layer management
* Add and manage geographic features on layers
* Manage feature properties with JSON schema
* Import and export data
* Generate GeoJSON and MapBox Vector Tile on single or group of layers
* Full management API available
* Optional PGRouting capabilities with plugin django-geostore-routing

## Requirements

### General

* Python 3.6+
* Postgresql 10+
* PostGIS 2.4+

Optionnal to use PgRouting functionnalities :
  * PgRouting 2.5+ and django-geostore-routing

### Libraries

these are debian packages required

- libpq-dev   (psycopg2)
- gettext     (translations)
- binutils    (django.contrib.gis)
- libproj-dev (django.contrib.gis)
- gdal-bin    (django.contrib.gis)

recommended

- postgresql-client (if you want to use ./manage.py dbshell command)

## Installation

### from PYPI

```bash
pip install django-geostore
```

### from GitHub

```bash
git clone https://github.com/Terralego/django-geostore.git
cd django-geostore
python3 setup.py install
```

### in your project settings

```python
INSTALLED_APPS = (
    'geostore',
)
```

## Development

### with docker :
```bash
docker-compose build
docker-compose up
docker-compose run web ./manage.py test
```

### with pip :
```bash
python3.6 -m venv venv
source activate venv/bin/activate
pip install -e .[dev]
```
