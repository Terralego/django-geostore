import json
from urllib.parse import unquote, urljoin

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import reverse

from ..models import Feature
from .. import settings as app_settings
from .helpers import VectorTile


class AbstractTileJsonMixin:
    response_class = HttpResponse
    content_type = 'application/json'

    @staticmethod
    def settings_link(layer, *args):
        layer_settings = layer.layer_settings_with_default(*args)
        if 'link' in layer_settings:
            return '<a href="{0}"/>{1}</a>'.format(
                layer_settings['link'].replace('"', '&quot;'),
                layer_settings['name'].replace('"', '&quot;'))
        return layer_settings

    @property
    def layers(self):
        raise NotImplementedError()

    def get_minzoom(self):
        return max(
            app_settings.MIN_TILE_ZOOM,
            min([
                l.layer_settings_with_default('tiles', 'minzoom')
                for l in self.layers
            ]))

    def get_maxzoom(self):
        return min(
            app_settings.MAX_TILE_ZOOM,
            max([
                l.layer_settings_with_default('tiles', 'maxzoom')
                for l in self.layers
            ]))

    def get_tile_path(self):
        return reverse("geostore:layer-tiles-pattern", args=[self.object.pk])

    def get_attribution(self):
        return ','.join(set(
            [
                l.layer_settings_with_default('metadata', 'attribution')
                for l in self.layers if l.layer_settings_with_default('metadata', 'attribution')
            ])) or None

    def get_description(self):
        return ','.join(set([
            a
            for a in [
                layer.layer_settings_with_default('metadata', 'description')
                for layer in self.layers
            ]
            if a
        ])) or None

    @staticmethod
    def layer_fields(layer):
        properties_filter = layer.layer_settings_with_default(
            'tiles', 'properties_filter')
        if properties_filter is not None:
            fields = properties_filter
        else:
            fields = layer.layer_properties.keys()

        return {f: '' for f in fields}

    def get_vector_layers(self):
        return [
            {
                'id': l.name,
                'fields': self.layer_fields(l),
                'minzoom': l.layer_settings_with_default('tiles', 'minzoom'),
                'maxzoom': l.layer_settings_with_default('tiles', 'maxzoom'),
            } for l in self.layers]

    def get_tilejson(self):
        minzoom = self.get_minzoom()
        maxzoom = self.get_maxzoom()

        tile_path = self.get_tile_path()

        # https://github.com/mapbox/tilejson-spec/tree/3.0/3.0.0
        return {
            'tilejson': '3.0.0',
            'name': self.object.name,
            'tiles': [
                unquote(urljoin(hostname, tile_path))
                for hostname in app_settings.TERRA_TILES_HOSTNAMES
            ],
            'minzoom': minzoom,
            'maxzoom': maxzoom,
            # bounds
            # center
            'attribution': self.get_attribution(),
            'description': self.get_description(),
            'vector_layers': self.get_vector_layers(),
        }

    def get_last_update(self):
        return (
            Feature.objects
            .filter(layer__in=self.layers)
            .order_by('-updated_at').first()
        )

    def render_to_response(self, context, **response_kwargs):
        self.object = self.get_object()
        last_update = self.get_last_update()

        if last_update:
            cache_key = f'tilejson-{self.object.name}'
            version = int(last_update.updated_at.timestamp())
            tilejson_data = cache.get(cache_key, version=version)

            if tilejson_data is None:
                tilejson_data = json.dumps(self.get_tilejson())
                cache.set(cache_key, tilejson_data, version=version)

            response_kwargs.setdefault('content_type', self.content_type)
            return self.response_class(
                content=tilejson_data,
                **response_kwargs,
            )

        return HttpResponseNotFound()


class TileJsonMixin(AbstractTileJsonMixin):

    @property
    def layers(self):
        return [self.object]


class MultipleTileJsonMixin(AbstractTileJsonMixin):

    @property
    def layers(self):
        return self.object.layers.all()


class TileResponseMixin:
    response_class = HttpResponse
    content_type = 'application/vnd.mapbox-vector-tile'

    def get_tile_for_layer(self, layer):
        tile = VectorTile(layer)
        features = layer.features.all()
        return tile.get_tile(
            self.kwargs['x'], self.kwargs['y'], self.kwargs['z'],
            layer.layer_settings_with_default('tiles', 'pixel_buffer'),
            layer.layer_settings_with_default('tiles', 'features_filter'),
            layer.layer_settings_with_default('tiles', 'properties_filter'),
            layer.layer_settings_with_default('tiles', 'features_limit'),
            features,
        )

    def get_tile(self, layer):
        minzoom = layer.layer_settings_with_default('tiles', 'minzoom')
        maxzoom = layer.layer_settings_with_default('tiles', 'maxzoom')
        if self.kwargs['z'] >= minzoom and self.kwargs['z'] <= maxzoom:
            feature_count, tile = self.get_tile_for_layer(layer)
        if feature_count:
            return tile
        return b''

    def render_to_response(self, context, **response_kwargs):
        layer = context['object']
        tile = self.get_tile(layer)

        response_kwargs.setdefault('content_type', self.content_type)
        return self.response_class(
            content=tile,
            **response_kwargs,
        )


class MultipleTileResponseMixin(TileResponseMixin):

    def get_tile(self, layers):
        return b''.join([
            super(MultipleTileResponseMixin, self).get_tile(layer)
            for layer in layers
        ])

    def render_to_response(self, context, **response_kwargs):
        layers = context['object'].layers.all()
        tile = self.get_tile(layers)

        response_kwargs.setdefault('content_type', self.content_type)
        return self.response_class(
            content=tile,
            **response_kwargs,
        )
