[![Build Status](https://travis-ci.org/Terralego/django-geostore.svg?branch=master)](https://travis-ci.org/Terralego/django-geostore/)
[![codecov](https://codecov.io/gh/Terralego/django-geostore/branch/master/graph/badge.svg)](https://codecov.io/gh/Terralego/django-geostore)
[![Maintainability](https://api.codeclimate.com/v1/badges/b6119d8175fa6f5f5949/maintainability)](https://codeclimate.com/github/Terralego/django-geostore/maintainability)
[![Documentation Status](https://readthedocs.org/projects/django-geostore/badge/?version=latest)](https://django-geostore.readthedocs.io/en/latest/?badge=latest)

# django-geostore

Dynamic geographic data store with Vector Tiles generation from PostGIS and json schema definition and validation.

## Create geographic layers

By :

* using django admin
* using geostore.Layer model
* Directly call an import command

### (optional) With fixed geometry type

* Accept only feature according a Geometry Type (see geostore.GeometryTypes)


### (optionnal) With json schema feature properties validation

* Define a schema in layer definition
* Using django admin or api will validate schema before saving. (use Feature.clean() method in custom cases) 

## Import data

There are several methods to import data in geostore

### Commands

* import_csv
* import_geojson
* import_osm
* import_shapefile

### API calls

### (optional) Group vector tiles layers, secure access by token

## Show group or single layer Vector Tiles on MapBox

## Show GeoJSON on MapBox

## Routing features


## Requirements

### General

* Python 3.6+
* Postgresql 10+
* PostGIS 2.4+
* PgRouting 2.5+

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
