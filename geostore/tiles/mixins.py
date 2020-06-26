from urllib.parse import unquote, urljoin

from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse, QueryDict
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.encoding import escape_uri_path
from django.utils.html import escape
from django.utils.timezone import now
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Feature
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

    def is_authorized(self, layer):
        if layer.authorized_groups.exists():
            return layer.authorized_groups.filter(pk__in=self.authenticated_groups).exists()
        return True


class MVTViewMixin(AuthenticatedGroupsMixin):
    tile_response_class = HttpResponse
    tile_content_type = 'application/vnd.mapbox-vector-tile'

    @action(detail=True, url_path=r'tiles/\{z\}/\{x\}/\{y\}', permission_classes=[], url_name='tiles-pattern')
    def tiles_pattern(self, request, *args, **kwargs):
        """ Fake pattern to reverse tile url """
        return Response(status=404)

    @action(detail=True, permission_classes=[])
    def tilejson(self, request, *args, **kwargs):
        """ MVT layer tilejson """
        last_update = self.get_last_update()
        cache_key = f'tilejson-{self.get_object().name}' + '-'.join([g.name for g in self.authenticated_groups])
        version = int(last_update.timestamp())
        tilejson_data = cache.get(cache_key, version=version)

        if not tilejson_data:
            tilejson_data = self.get_tilejson()
            cache.set(cache_key, tilejson_data, version=version)
        return Response(tilejson_data)

    @action(detail=True, url_name='tiles', permission_classes=[],
            url_path=r'tiles/(?P<z>[\d-]+)/(?P<x>[\d-]+)/(?P<y>[\d-]+)', )
    def tiles(self, request, z, x, y, **kwargs):
        return self.tile_response_class(
            self.get_tile(int(z), int(x), int(y)),
            content_type=self.tile_content_type
        )

    def get_tile_for_layer(self, layer, z, x, y):
        tile = VectorTile(layer)
        return tile.get_tile(
            x, y, z
        )

    def get_tile(self, z, x, y):
        tiles_array = []
        for layer in self.layers:
            minzoom = layer.layer_settings_with_default('tiles', 'minzoom')
            maxzoom = layer.layer_settings_with_default('tiles', 'maxzoom')
            if minzoom <= z <= int(maxzoom) and self.is_authorized(layer):
                unused, tile = self.get_tile_for_layer(layer, z, x, y)
                tiles_array.append(tile)

            for extra_layer in layer.extra_geometries.all():
                unused, tile = self.get_tile_for_layer(extra_layer, z, x, y)
                tiles_array.append(tile)

        return b''.join(tiles_array)

    def get_tile_path(self):
        return self.get_tokenized_url(
            reverse("layer-tiles-pattern", args=[self.get_object().pk])
        )

    @cached_property
    def layers(self):
        # keep a qs result here

        return type(self.get_object()).objects.filter(
            Q(pk=self.get_object().pk) &
            (
                Q(authorized_groups__isnull=True) | Q(authorized_groups__in=self.authenticated_groups)
            )
        )

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

    def get_min_zoom(self):
        return max(
            app_settings.MIN_TILE_ZOOM,
            min([
                layer.layer_settings_with_default('tiles', 'minzoom')
                for layer in self.layers
            ], default=app_settings.MIN_TILE_ZOOM))

    def get_max_zoom(self):
        return min(
            app_settings.MAX_TILE_ZOOM,
            max([
                layer.layer_settings_with_default('tiles', 'maxzoom')
                for layer in self.layers
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
        data = []
        for layer in self.layers:
            data.append({
                'id': layer.name,
                'description': layer.name.title(),
                'fields': self.layer_fields(layer),
                'minzoom': layer.layer_settings_with_default('tiles', 'minzoom'),
                'maxzoom': layer.layer_settings_with_default('tiles', 'maxzoom'),
            })
            for extra_geom in layer.extra_geometries.all():
                data.append({
                    'id': f'{extra_geom.name}',
                    'description': f'{extra_geom.title}'.title(),
                    'fields': {},
                    'minzoom': layer.layer_settings_with_default('tiles', 'minzoom'),
                    'maxzoom': layer.layer_settings_with_default('tiles', 'maxzoom'),
                })

        return data

    def get_tile_urls(self, tile_pattern):
        if app_settings.TERRA_TILES_HOSTNAMES:
            return [
                unquote(urljoin(hostname, tile_pattern))
                for hostname in app_settings.TERRA_TILES_HOSTNAMES
            ]
        else:
            return [
                unquote(urljoin(self.request.build_absolute_uri('/'), tile_pattern))
            ]

    def get_tilejson(self):
        minzoom = self.get_min_zoom()
        maxzoom = self.get_max_zoom()

        tile_pattern = self.get_tile_path()

        # https://github.com/mapbox/tilejson-spec/tree/3.0/3.0.0
        return {
            'tilejson': '3.0.0',
            'name': self.get_object().name,
            'tiles': self.get_tile_urls(tile_pattern),
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
            ref_object = self.layers.order_by('-updated_at').first()

        return ref_object.updated_at if ref_object else now()


class MultipleMVTViewMixin(MVTViewMixin):
    def get_tile_path(self):
        return self.get_tokenized_url(
            reverse("group-tiles-pattern", args=[self.get_object().slug])
        )

    @cached_property
    def layers(self):
        # Get the non authentified layers
        return self.get_object().layers.filter(
            Q(authorized_groups__isnull=True) |
            Q(authorized_groups__in=self.authenticated_groups)
        )
