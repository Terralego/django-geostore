from urllib.parse import unquote

import jsonschema
from django.urls import reverse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from terracommon.accounts.mixins import UserTokenGeneratorMixin
from terracommon.terra.models import (Feature, FeatureRelation, Layer,
                                      LayerRelation)


class PropertiesSerializer(serializers.ModelSerializer):
    properties = serializers.JSONField()

    def validate_properties(self, value):
        """
        Properties should be valid json, and valid data according layer's schema
        """
        layer = self.context.get('layer')
        if layer and layer.schema:
            # validate properties according layer schema definition
            try:
                jsonschema.validate(value, layer.schema)

            except jsonschema.exceptions.ValidationError as exc:
                raise ValidationError(detail=exc.message)

        return value


class FeatureSerializer(PropertiesSerializer):
    class Meta:
        model = Feature
        fields = ('id', 'geom', 'layer', 'properties', )
        read_only_fields = ('id', 'layer')


class FeatureInLayerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feature
        fields = ('id', 'geom', )


class LayerSerializer(serializers.ModelSerializer, UserTokenGeneratorMixin):
    group_intersect = serializers.SerializerMethodField()
    group_tilejson = serializers.SerializerMethodField()
    group_tiles = serializers.SerializerMethodField()
    routing_url = serializers.SerializerMethodField()
    shapefile_url = serializers.SerializerMethodField()
    geojson_url = serializers.SerializerMethodField()

    def get_group_intersect(self, obj):
        return reverse('terra:layer-intersects', args=[obj.name, ])

    def get_group_tilejson(self, obj):
        return unquote(reverse('terra:group-tilejson', args=[obj.group]))

    def get_group_tiles(self, obj):
        return unquote(reverse('terra:group-tiles-pattern', args=[obj.group]))

    def get_routing_url(self, obj):
        return reverse('terra:layer-route', args=[obj.pk, ])

    def get_token(self, obj, type):
        if self.current_user.is_anonymous:
            return None

        uidb64, token = self.get_uidb64_token_for_user(self.current_user)
        return "{}?uidb64={}&token={}".format(
            reverse('terra:layer-%s' % type, args=[obj.pk, ]),
            uidb64,
            token)

    def get_shapefile_url(self, obj):
        return self.get_token(obj, "shapefile")

    def get_geojson_url(self, obj):
        return self.get_token(obj, "geojson")

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


class FeatureRelationSerializer(PropertiesSerializer):
    schema_model = LayerRelation

    class Meta:
        model = FeatureRelation
        fields = ('id', 'origin', 'destination')
