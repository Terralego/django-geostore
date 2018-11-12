import json
from urllib.parse import unquote

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import reverse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from ..models import Layer
from .helpers import VectorTile


class TilejsonView(APIView):

    permission_classes = ()

    def get_tilejson(self, base_url, group):
        minzoom = max(
            settings.MIN_TILE_ZOOM,
            min(self.layers, key=lambda l: l.tiles_minzoom).tiles_minzoom)
        maxzoom = min(
            settings.MAX_TILE_ZOOM,
            max(self.layers, key=lambda l: l.tiles_maxzoom).tiles_maxzoom)
        tile_path = unquote(reverse("group-tiles-pattern", args=[group]))

        # https://github.com/mapbox/tilejson-spec/tree/3.0/3.0.0
        return {
            'tilejson': '3.0.0',
            'name': group,
            'tiles': [
                f'{base_url}{tile_path}'
            ],
            'minzoom': minzoom,
            'maxzoom': maxzoom,
            # bounds
            # center
            'vector_layers': [{
                'id': layer.name,
                'fields': self.layer_fields(layer),
                'minzoom': layer.tiles_minzoom,
                'maxzoom': layer.tiles_maxzoom,
            } for layer in self.layers]
        }

    def layer_fields(self, layer):
        if layer.tiles_properties_filter is not None:
            fileds = layer.tiles_properties_filter
        else:
            fileds = layer.layer_properties.keys()

        return {f: '' for f in fileds}

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

        base_url = f'{request.scheme}://{request.META["HTTP_HOST"]}'
        return HttpResponse(
            json.dumps(self.get_tilejson(base_url, group)),
            content_type='application/json')


class MVTView(APIView):

    permission_classes = ()

    def get_tile(self):
        big_tile = b''

        for layer in self.layers:
            if self.z >= layer.tiles_minzoom and self.z <= layer.tiles_maxzoom:
                feature_count, tile = self.get_tile_for_layer(layer)
                if feature_count:
                    big_tile += tile
        return big_tile

    def get_tile_for_layer(self, layer):
        tile = VectorTile(layer)
        features = layer.features.all()
        return tile.get_tile(
            self.x, self.y, self.z,
            layer.tiles_pixel_buffer,
            layer.tiles_properties_filter,
            layer.tiles_features_limit,
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
