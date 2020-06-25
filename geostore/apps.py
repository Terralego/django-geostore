from django.apps import AppConfig
from django.conf import settings


class GeostoreConfig(AppConfig):
    name = 'geostore'
    verbose_name = "Geographic Store"

    def ready(self):
        # Set default settings from this app to django.settings if not present
        from . import settings as defaults
        dj_settings = settings._wrapped.__dict__
        for name in dir(defaults):
            dj_settings.setdefault(name, getattr(defaults, name))
        # force use specific geojson serializer
        modules = getattr(settings, 'SERIALIZATION_MODULES', {})
        modules.update({
            'geojson': 'geostore.serializers.geojson',
        })
        setattr(settings, 'SERIALIZATION_MODULES', modules)
