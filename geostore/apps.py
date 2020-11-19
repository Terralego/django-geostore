from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class GeostoreConfig(AppConfig):
    name = 'geostore'
    verbose_name = _("Geographic Store")

    def ready(self):
        # force use specific geojson serializer
        modules = getattr(settings, 'SERIALIZATION_MODULES', {})
        modules.update({
            'geojson': 'geostore.serializers.geojson',
        })
        setattr(settings, 'SERIALIZATION_MODULES', modules)

        import geostore.signals  # NOQA
        import geostore.db.lookups  # NOQA
