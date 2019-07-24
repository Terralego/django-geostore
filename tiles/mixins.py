from django.http import HttpResponse

from .helpers import VectorTile


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
