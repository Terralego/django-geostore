[![Build Status](https://travis-ci.org/Terralego/terralego.backend.terra.svg?branch=master)](https://travis-ci.org/Terralego/terralego.backend.terra/)
[![codecov](https://codecov.io/gh/Terralego/terralego.backend.terra/branch/master/graph/badge.svg)](https://codecov.io/gh/Terralego/terralego.backend.terra)
[![Maintainability](https://api.codeclimate.com/v1/badges/74b0d8430ff982633ee7/maintainability)](https://codeclimate.com/github/Terralego/terralego.backend.terra/maintainability)
[![Documentation Status](https://readthedocs.org/projects/terralegobackendterra/badge/?version=latest)](https://terralegobackendterra.readthedocs.io/en/latest/?badge=latest)

![Python Version](https://img.shields.io/badge/python-%3E%3D%203.6-blue.svg)
![Django Version](https://img.shields.io/badge/django-%3E%3D%202.1%2C<3.0-blue.svg)
![Rest Version](https://img.shields.io/badge/django--rest--framework-%3E%3D%203.8.0-blue)

# BACKWARD compatibility

## settings to add :

```python
import os

....

MEDIA_ACCEL_REDIRECT = os.getenv('MEDIA_ACCEL_REDIRECT', default="False") == "True"
HOSTNAME = os.environ.get('HOSTNAME', '')

```
