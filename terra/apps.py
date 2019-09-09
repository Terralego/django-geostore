from django.apps import AppConfig
from django.conf import settings


class TerraConfig(AppConfig):
    name = "terra"
    verbose_name = "Terralego Geographic Store"

    def ready(self):
        # force use specific geojson serializer
        modules = getattr(settings, "SERIALIZATION_MODULES", {})
        modules.update({"geojson": "terra.serializers.geojson"})
        setattr(settings, "SERIALIZATION_MODULES", modules)
