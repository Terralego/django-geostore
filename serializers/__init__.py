from django.urls import reverse
from django.utils.http import urlunquote
from rest_framework import serializers

from terracommon.terra.models import (Feature, FeatureRelation, Layer,
                                      LayerRelation)
from terracommon.terra.validators import validate_json_schema_data, validate_json_schema


class FeatureSerializer(serializers.ModelSerializer):
    properties = serializers.JSONField(required=False)

    def validate_properties(self, data):
        """
        Validate schema if exists
        """
        if self.context.get('layer_pk'):
            layer = Layer.objects.get(pk=self.context.get('layer_pk'))
            validate_json_schema_data(data, layer.schema)
        return data

    class Meta:
        model = Feature
        fields = ('id', 'identifier', 'layer', 'geom', 'properties', )
        read_only_fields = ('id', 'layer')


class LayerSerializer(serializers.ModelSerializer):
    group_intersect = serializers.SerializerMethodField()
    group_tilejson = serializers.SerializerMethodField()
    group_tiles = serializers.SerializerMethodField()
    routing_url = serializers.SerializerMethodField()
    shapefile_url = serializers.SerializerMethodField()
    geojson_url = serializers.SerializerMethodField()
    schema = serializers.JSONField(required=False, validators=[validate_json_schema])

    def get_group_intersect(self, obj):
        return reverse('terra:layer-intersects', args=[obj.name, ])

    def get_group_tilejson(self, obj):
        return urlunquote(reverse('terra:group-tilejson', args=[obj.group]))

    def get_group_tiles(self, obj):
        return urlunquote(reverse('terra:group-tiles-pattern', args=[obj.group]))

    def get_routing_url(self, obj):
        return reverse('terra:layer-route', args=[obj.pk, ])

    def get_shapefile_url(self, obj):
        return reverse('terra:layer-shapefile', args=[obj.pk, ])

    def get_geojson_url(self, obj):
        return reverse('terra:layer-geojson', args=[obj.pk, ])

    class Meta:
        model = Layer
        fields = '__all__'


class GeoJSONLayerSerializer(serializers.JSONField):
    def to_representation(self, data):
        return data.to_geojson()


class LayerRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerRelation
        fields = ('id', 'origin', 'destination', 'schema')


class FeatureRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureRelation
        fields = ('id', 'origin', 'destination')
