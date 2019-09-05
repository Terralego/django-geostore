[![Build Status](https://travis-ci.org/Terralego/terra.backend.terra.svg?branch=master)](https://travis-ci.org/Terralego/terra.backend.terra/)
[![codecov](https://codecov.io/gh/Terralego/terra.backend.terra/branch/master/graph/badge.svg)](https://codecov.io/gh/Terralego/terra.backend.terra)
[![Maintainability](https://api.codeclimate.com/v1/badges/74b0d8430ff982633ee7/maintainability)](https://codeclimate.com/github/Terralego/terralego.backend.terra/maintainability)
[![Documentation Status](https://readthedocs.org/projects/terralegobackendterra/badge/?version=latest)](https://terralegobackendterra.readthedocs.io/en/latest/?badge=latest)

# BACKWARD compatibility

## settings to add :

```python
import os

#####

MEDIA_ACCEL_REDIRECT = os.getenv('MEDIA_ACCEL_REDIRECT', default="False") == "True"
HOSTNAME = os.environ.get('HOSTNAME', '')

SERIALIZATION_MODULES = {
    'geojson': 'terra.serializers.geojson',
}
```
