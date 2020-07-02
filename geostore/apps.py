from django.apps import AppConfig
from django.conf import settings


class GeostoreConfig(AppConfig):
    name = 'geostore'
    verbose_name = "Geographic Store"

    def ready(self):
        # execute checks
        from . import checks  # NOQA
        # force use specific geojson serializer
        modules = getattr(settings, 'SERIALIZATION_MODULES', {})
        modules.update({
            'geojson': 'geostore.serializers.geojson',
        })
        setattr(settings, 'SERIALIZATION_MODULES', modules)
