
from django.contrib.gis.serializers import geojson as basegeojson


class Serializer(basegeojson.Serializer):
    def _init_options(self):
        super()._init_options()
        self.properties_field = self.json_kwargs.pop('properties_field', None)

    def handle_field(self, obj, field):
        if field.name == self.properties_field:
            self._current = field.value_from_object(obj)
        else:
            super().handle_field(obj, field)
