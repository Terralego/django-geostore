[![Build Status](https://travis-ci.org/Terralego/django-geostore.svg?branch=master)](https://travis-ci.org/Terralego/django-geostore/)
[![codecov](https://codecov.io/gh/Terralego/django-geostore/branch/master/graph/badge.svg)](https://codecov.io/gh/Terralego/django-geostore)
[![Maintainability](https://api.codeclimate.com/v1/badges/b6119d8175fa6f5f5949/maintainability)](https://codeclimate.com/github/Terralego/django-geostore/maintainability)
[![Documentation Status](https://readthedocs.org/projects/django-geostore/badge/?version=latest)](https://django-geostore.readthedocs.io/en/latest/?badge=latest)

![Python Version](https://img.shields.io/badge/python-%3E%3D%203.6-blue.svg)
![Django Version](https://img.shields.io/badge/django-%3E%3D%202.2%2C<3.1-blue.svg)
![Rest Version](https://img.shields.io/badge/django--rest--framework-%3E%3D%203.10.0-blue)

# django-geostore

Dynamic geo data store with vector tiles generation and json schema definition / validation

## Requirements

* Postgresql 10+
* PostGIS 2.4+
* PgRouting 2.5+

## Development

### with docker :
```bash
$ docker-compose build
$ docker-compose up
$ docker-compose run web /code/venv/bin/python3.7 ./manage.py test
```

### with pip :
```bash
$ python3.7 -m venv venv
$ source activate venv/bin/activate
pip install -e .[dev]
```
