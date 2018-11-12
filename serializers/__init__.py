from urllib.parse import unquote

from django.shortcuts import get_object_or_404
from django.urls import reverse

from rest_framework import serializers

from terracommon.accounts.mixins import UserTokenGeneratorMixin
from terracommon.terra.models import Layer, Feature, LayerRelation, \
                                     FeatureRelation


class PropertiesSerializer(serializers.ModelSerializer):
    """
    Serialize models with a 'properties' field described by the 'schema' field
    of 'schema_model'
    The properties are dynamically flattened with other static fields.
    The viewset url must contains a parameter named against model name suffixed
    by '_pk'.
    """
    schema_model = None

    def get_fields(self):
        pk_url_kwarg = f'{self.schema_model._meta.model_name}_pk'
        schema_object = get_object_or_404(
                            self.schema_model,
                            pk=self.context['view'].kwargs[pk_url_kwarg]
                        )
        fields = super().get_fields()
        for name, description in schema_object.schema.items():
            Field = {
                'integer': serializers.IntegerField,
                'string': serializers.CharField,
            }[description['type']]
            fields.update({name: Field(source=f'properties.{name}')})
        return fields


class FeatureSerializer(PropertiesSerializer):
    schema_model = Layer

    class Meta:
        model = Feature
        fields = ('id', 'geom', 'layer', 'properties', )


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
        return reverse('layer-intersects', args=[obj.name, ])

    def get_group_tilejson(self, obj):
        return unquote(reverse('group-tilejson', args=[obj.group]))

    def get_group_tiles(self, obj):
        return unquote(reverse('group-tiles-pattern', args=[obj.group]))

    def get_routing_url(self, obj):
        return reverse('layer-route', args=[obj.pk, ])

    def get_token(self, obj, type):
        if self.current_user.is_anonymous:
            return None

        uidb64, token = self.get_uidb64_token_for_user(self.current_user)
        return "{}?uidb64={}&token={}".format(
            reverse('layer-%s' % type, args=[obj.pk, ]),
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
