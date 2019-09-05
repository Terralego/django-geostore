Configuration
=============


In your project :

* settings

::

    INSTALLED_APPS = [
        ...
        'rest_framework',
        'terra',
        ...
    ]

* urls

::

    urlpatterns = [
        ...
        path('', include('terra.urls', namespace='terra')),
        ...
    ]

You can customize default url and namespace by including terra.views directly

Run migrations

::

    ./manage.py migrate



- ADMIN :

you can disable and / or customize admin


- SETTINGS :

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
