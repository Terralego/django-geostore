from datetime import datetime
import json
from urllib.parse import unquote, urljoin

from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse, QueryDict
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.encoding import escape_uri_path
from django.utils.html import escape

from ..models import Feature, Layer
from .. import settings as app_settings
from ..tokens import tiles_token_generator
from .helpers import VectorTile


class AuthenticatedGroupsMixin:

    IDB64_QUERY_ARG = 'idb64'
    TOKEN_QUERY_ARG = 'token'

    @cached_property
    def authenticated_groups(self):
        token, idb64 = self.request.GET.get(self.TOKEN_QUERY_ARG), self.request.GET.get(self.IDB64_QUERY_ARG)
        if token and idb64:
            groups, layergroup = tiles_token_generator.decode_idb64(idb64)

            if groups and layergroup and tiles_token_generator.check_token(token, groups, layergroup):
                return groups
        return []


class AbstractTileJsonMixin(AuthenticatedGroupsMixin):
    response_class = HttpResponse
    content_type = 'application/json'

    def get_tokenized_url(self, url):
        if self.authenticated_groups:
            querystring = QueryDict(mutable=True)
            querystring.update({
                self.IDB64_QUERY_ARG: self.request.GET.get(self.IDB64_QUERY_ARG),
                self.TOKEN_QUERY_ARG: self.request.GET.get(self.TOKEN_QUERY_ARG)
            })
            return f'{url}?{querystring.urlencode()}'
        return url

    @staticmethod
    def settings_link(layer, *args):
        layer_settings = layer.layer_settings_with_default(*args)
        if 'link' in layer_settings:
            return '<a href="{0}"/>{1}</a>'.format(
                escape_uri_path(layer_settings['link']),
                escape(layer_settings['name'])
            )
        return layer_settings

    @property
    def layers(self):
        raise NotImplementedError()

    def get_tile_path(self):
        raise NotImplementedError()

    def get_minzoom(self):
        return max(
            app_settings.MIN_TILE_ZOOM,
            min([
                l.layer_settings_with_default('tiles', 'minzoom')
                for l in self.layers
            ], default=app_settings.MIN_TILE_ZOOM))

    def get_maxzoom(self):
        return min(
            app_settings.MAX_TILE_ZOOM,
            max([
                l.layer_settings_with_default('tiles', 'maxzoom')
                for l in self.layers
            ], default=app_settings.MAX_TILE_ZOOM))

    def _join_group_settings_link(self, layers, *args):
        return ','.join(set([
            a if 'link' not in a else
            '<a href="{0}"/>{1}</a>'.format(escape_uri_path(a['link']), escape(a['name']))
            for a in [layer.layer_settings_with_default(*args) for layer in self.layers]
            if a
        ])) or None

    def _join_group_settings_string(self, layers, *args):
        return ','.join(set([
            a
            for a in [layer.layer_settings_with_default(*args) for layer in self.layers]
            if a
        ])) or None

    def get_attribution(self):
        return self._join_group_settings_link(self.layers, 'metadata', 'attribution')

    def get_description(self):
        return self._join_group_settings_string(self.layers, 'metadata', 'description')

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
        features = Feature.objects.filter(layer__in=self.layers).order_by('-updated_at')

        if features.exists():
            ref_object = features.first()
        else:
            ref_object = Layer.objects.filter(pk__in=self.layers).order_by('-updated_at').first()

        if ref_object:
            return ref_object.updated_at

        return datetime.now()

    def render_to_response(self, context, **response_kwargs):
        self.object = self.get_object()
        last_update = self.get_last_update()

        cache_key = f'tilejson-{self.object.name}' + '-'.join([g.name for g in self.authenticated_groups])
        version = int(last_update.timestamp())
        tilejson_data = cache.get(cache_key, version=version)

        if tilejson_data is None:
            tilejson_data = json.dumps(self.get_tilejson())
            cache.set(cache_key, tilejson_data, version=version)

        response_kwargs.setdefault('content_type', self.content_type)
        return self.response_class(
            content=tilejson_data,
            **response_kwargs,
        )


class TileJsonMixin(AbstractTileJsonMixin):
    def get_tile_path(self):
        return self.get_tokenized_url(
            reverse("geostore:layer-tiles-pattern", args=[self.object.pk])
        )

    @cached_property
    def layers(self):
        # keep a qs result here
        return type(self.object).objects.filter(
            Q(pk=self.object.pk) &
            (
                Q(authorized_groups__isnull=True) | Q(authorized_groups__in=self.authenticated_groups)
            )
        )


class MultipleTileJsonMixin(AbstractTileJsonMixin):
    def get_tile_path(self):
        return self.get_tokenized_url(
            reverse("geostore:group-tiles-pattern", args=[self.object.slug])
        )

    @cached_property
    def layers(self):
        # Get the non authentified layers
        return self.object.layers.filter(
            Q(authorized_groups__isnull=True) |
            Q(authorized_groups__in=self.authenticated_groups)
        )


class TileResponseMixin(AuthenticatedGroupsMixin):
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

    def is_authorized(self, layer):
        if layer.authorized_groups.exists():
            return layer.authorized_groups.filter(pk__in=self.authenticated_groups).exists()
        return True

    def get_tile(self, layer):
        minzoom = layer.layer_settings_with_default('tiles', 'minzoom')
        maxzoom = layer.layer_settings_with_default('tiles', 'maxzoom')
        if self.kwargs['z'] >= minzoom and self.kwargs['z'] <= maxzoom and self.is_authorized(layer):
            _, tile = self.get_tile_for_layer(layer)
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
