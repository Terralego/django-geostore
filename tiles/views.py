import json
from urllib.parse import unquote, urljoin

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.detail import BaseDetailView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from ..models import Feature, Layer, LayerGroup
from .mixins import MultipleTileResponseMixin, TileResponseMixin


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

    def get_tilejson(self, group=None, layer=None):
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
        if group:
            tile_path = reverse("terra:group-tiles-pattern", args=[group.slug])
        else:
            tile_path = reverse("terra:layer-tiles-pattern", args=[layer.pk])

        # https://github.com/mapbox/tilejson-spec/tree/3.0/3.0.0
        return {
            'tilejson': '3.0.0',
            'name': group.name if group else layer.name,
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
    def get(self, request, slug=None, pk=None):
        if slug:
            group = get_object_or_404(LayerGroup, slug=slug)
            self.layers = group.layers.all()
        else:
            layer = get_object_or_404(Layer, pk=pk)
            self.layers = [layer]

        if len(self.layers) == 0:
            return HttpResponseNotFound()

        last_update = Feature.objects.filter(layer__in=self.layers).order_by('-updated_at').first()

        if last_update:
            if slug:
                cache_key = f'tilejson-{group.slug}'
            else:
                cache_key = f'tilejson-{layer.name}'
            version = int(last_update.updated_at.timestamp())
            tilejson_data = cache.get(cache_key, version=version)

            if tilejson_data is None:
                if slug:
                    tilejson_data = json.dumps(self.get_tilejson(group=group))
                else:
                    tilejson_data = json.dumps(self.get_tilejson(layer=layer))
                cache.set(cache_key, tilejson_data, version=version)

            return HttpResponse(
                tilejson_data,
                content_type='application/json')

        return HttpResponseNotFound()


class LayerTileDetailView(TileResponseMixin, BaseDetailView):
    model = Layer


class LayerGroupTileDetailView(MultipleTileResponseMixin, BaseDetailView):
    model = LayerGroup
