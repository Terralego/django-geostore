import json
from urllib.parse import unquote, urljoin

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import reverse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from ..models import Feature, Layer
from .helpers import VectorTile


class TilejsonView(APIView):

    permission_classes = ()

    def _join_group_settings_link(self, layers, *args):
        return ','.join(set([
            a if 'link' not in a else
            '<a href="{0}"/>{1}</a>'.format(a['link'].replace('"', '&quot;'), a['name'].replace('"', '&quot;'))
            for a in [layer.layer_settings_with_default(*args) for layer in self.layers]
            if a
        ])) or None

    def _join_group_settings_string(self, layers, *args):
        return ','.join(set([
            a
            for a in [layer.layer_settings_with_default(*args) for layer in self.layers]
            if a
        ])) or None

    def get_tilejson(self, group):
        minzoom = max(
            settings.MIN_TILE_ZOOM,
            min(map(
                lambda l: l.layer_settings_with_default('tiles', 'minzoom'),
                self.layers)))
        maxzoom = min(
            settings.MAX_TILE_ZOOM,
            max(map(
                lambda l: l.layer_settings_with_default('tiles', 'maxzoom'),
                self.layers)))
        tile_path = reverse("terra:group-tiles-pattern", args=[group])

        # https://github.com/mapbox/tilejson-spec/tree/3.0/3.0.0
        return {
            'tilejson': '3.0.0',
            'name': group,
            'tiles': [
                unquote(urljoin(hostname, tile_path))
                for hostname in settings.TERRA_TILES_HOSTNAMES
            ],
            'minzoom': minzoom,
            'maxzoom': maxzoom,
            # bounds
            # center
            "attribution": self._join_group_settings_link(self.layers, 'metadata', 'attribution'),
            "description": self._join_group_settings_string(self.layers, 'metadata', 'description'),
            'vector_layers': [{
                'id': layer.name,
                'fields': self.layer_fields(layer),
                'minzoom': layer.layer_settings_with_default(
                    'tiles', 'minzoom'),
                'maxzoom': layer.layer_settings_with_default(
                    'tiles', 'maxzoom'),
            } for layer in self.layers]
        }

    def layer_fields(self, layer):
        properties_filter = layer.layer_settings_with_default(
            'tiles', 'properties_filter')
        if properties_filter is not None:
            fields = properties_filter
        else:
            fields = layer.layer_properties.keys()

        return {f: '' for f in fields}

    @swagger_auto_schema(
        responses={
            200: 'Returns a protobuf mapbox vector tile',
            404: 'The layer group does not exist'
            }
    )
    def get(self, request, group):
        self.layers = Layer.objects.filter(group=group)

        if self.layers.count() == 0:
            return HttpResponseNotFound()

        last_update = Feature.objects.filter(layer__in=self.layers).order_by('-updated_at').first()

        if last_update:
            cache_key = f'tilejson-{group}'
            version = int(last_update.updated_at.timestamp())
            tilejson_data = cache.get(cache_key, version=version)

            if tilejson_data is None:
                tilejson_data = json.dumps(self.get_tilejson(group))
                cache.set(cache_key, tilejson_data, version=version)

            return HttpResponse(
                tilejson_data,
                content_type='application/json')

        return HttpResponseNotFound()


class MVTView(APIView):

    permission_classes = ()

    def get_tile(self):
        big_tile = b''

        for layer in self.layers:
            minzoom = layer.layer_settings_with_default('tiles', 'minzoom')
            maxzoom = layer.layer_settings_with_default('tiles', 'maxzoom')
            if self.z >= minzoom and self.z <= maxzoom:
                feature_count, tile = self.get_tile_for_layer(layer)
                if feature_count:
                    big_tile += tile
        return big_tile

    def get_tile_for_layer(self, layer):
        tile = VectorTile(layer)
        features = layer.features.all()
        return tile.get_tile(
            self.x, self.y, self.z,
            layer.layer_settings_with_default('tiles', 'pixel_buffer'),
            layer.layer_settings_with_default('tiles', 'features_filter'),
            layer.layer_settings_with_default('tiles', 'properties_filter'),
            layer.layer_settings_with_default('tiles', 'features_limit'),
            features)

    @swagger_auto_schema(
        responses={
            200: 'Returns a protobuf mapbox vector tile',
            404: 'The layer group does not exist'
            }
    )
    def get(self, request, group, z, x, y):
        if z > settings.MAX_TILE_ZOOM or z < settings.MIN_TILE_ZOOM:
            return HttpResponse(status=204)
        self.z = z
        self.x = x
        self.y = y

        self.layers = Layer.objects.filter(group=group)

        if self.layers.count() == 0:
            return HttpResponseNotFound()

        return HttpResponse(
                    self.get_tile(),
                    content_type="application/vnd.mapbox-vector-tile"
                    )
