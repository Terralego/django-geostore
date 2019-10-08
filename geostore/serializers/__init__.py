from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.http import urlunquote
from rest_framework import serializers
from rest_framework.fields import empty

from geostore.models import (Feature, FeatureRelation, Layer,
                             LayerRelation, LayerGroup)
from geostore.validators import (validate_json_schema_data,
                                 validate_json_schema, validate_geom_type)


class FeatureSerializer(serializers.ModelSerializer):
    properties = serializers.JSONField(required=False)

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance=instance, data=data, **kwargs)
        self.layer = None

    def get_layer(self):
        if self.instance:
            self.layer = self.instance.layer
        if not self.layer and self.context.get('layer_pk'):
            self.layer = Layer.objects.get(pk=self.context.get('layer_pk'))
        return self.layer

    def validate_geom(self, data):
        """
        Validate geom exists
        """
        if self.get_layer():
            validate_geom_type(self.get_layer().geom_type, data.geom_typeid)
        return data

    def validate_properties(self, data):
        """
        Validate schema if exists
        """
        if self.get_layer():
            validate_json_schema_data(data, self.get_layer().schema)
        return data

    class Meta:
        model = Feature
        fields = ('id', 'identifier', 'layer', 'geom', 'properties', )
        read_only_fields = ('id', 'layer')


class GroupSerializer(serializers.ModelSerializer):
    tilejson = serializers.SerializerMethodField()
    group_tiles = serializers.SerializerMethodField()

    def get_tilejson(self, obj):
        return urlunquote(reverse('geostore:group-tilejson', args=[obj.slug]))

    def get_group_tiles(self, obj):
        return urlunquote(reverse('geostore:group-tiles-pattern', args=[obj.slug]))

    class Meta:
        model = LayerGroup
        fields = '__all__'


class LayerSerializer(serializers.ModelSerializer):
    routing_url = serializers.SerializerMethodField()
    shapefile_url = serializers.SerializerMethodField()
    geojson_url = serializers.SerializerMethodField()
    schema = serializers.JSONField(required=False, validators=[validate_json_schema])
    layer_intersects = serializers.SerializerMethodField()
    tilejson = serializers.SerializerMethodField()
    layer_groups = GroupSerializer(many=True, read_only=True)
    authorized_groups = serializers.PrimaryKeyRelatedField(required=False, many=True, queryset=Group.objects.all())

    def get_routing_url(self, obj):
        return reverse('geostore:layer-route', args=[obj.pk, ])

    def get_shapefile_url(self, obj):
        return reverse('geostore:layer-shapefile', args=[obj.pk, ])

    def get_geojson_url(self, obj):
        return reverse('geostore:layer-geojson', args=[obj.pk, ])

    def get_layer_intersects(self, obj):
        return reverse('geostore:layer-intersects', args=[obj.name, ])

    def get_tilejson(self, obj):
        return urlunquote(reverse('geostore:layer-tilejson', args=[obj.pk]))

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
