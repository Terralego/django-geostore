from django.contrib.gis.serializers import geojson as basegeojson
from rest_framework_gis.serializers import GeoFeatureModelSerializer


class Serializer(basegeojson.Serializer):
    def _init_options(self):
        super()._init_options()
        self.properties_field = self.json_kwargs.pop('properties_field', None)

    def handle_field(self, obj, field):
        if field.name == self.properties_field:
            self._current = field.value_from_object(obj)
        else:
            super().handle_field(obj, field)


class FinalGeoJSONSerializer(GeoFeatureModelSerializer):
    def get_properties(self, instance, fields):
        geojson_properties = super().get_properties(instance, fields)
        instance_properties = geojson_properties.pop('properties')
        for field in instance_properties:
            geojson_properties[field] = instance_properties[field]
        return geojson_properties

    class Meta:
        geo_field = 'geom'
