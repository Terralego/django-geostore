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
