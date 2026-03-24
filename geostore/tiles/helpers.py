from hashlib import sha224
from random import uniform

from django.contrib.gis.db.models.functions import Transform
from django.core.cache import cache
from django.db import connection
from math import ceil, floor, log, pi

from vectortiles.backends.postgis import VectorLayer

from . import EARTH_RADIUS, EPSG_3857
from .sigtools import SIGTools


def get_cache_version(layer):
    try:
        return int(layer.features.order_by('-updated_at').first().updated_at.timestamp())
    except AttributeError:
        # This happens when a layer is empty
        return 1


def cached_tile(func):
    def wrapper(self, x, y, z,
                *args, **kwargs):
        cache_key = self.get_tile_cache_key(x, y, z)
        version = get_cache_version(self.layer)
        expiration_factor = (log(5, z) ** 0.9)

        # Cache expiry calculation is based on a logarithmic function where we add a random factor of +-10%
        expiration = int(expiration_factor * (3600 * 24 * 7) * uniform(0.9, 1.1))

        def build_tile():
            return func(
                self, x, y, z, *args, **kwargs)

        return cache.get_or_set(cache_key, build_tile, expiration, version=version)

    return wrapper


class GeoStoreVectorLayer(VectorLayer):
    """Adapter between geostore Layer model and django-vectortiles VectorLayer"""

    def __init__(self, layer, name=None, description=None, features_pk=None,
                 cache_key=None, include_fields=True, min_zoom=None, max_zoom=None):
        self.layer = layer
        self._name = name or layer.name
        self._description = description
        self.features_pk = features_pk
        self._cache_key = cache_key
        self._include_fields = include_fields
        self._min_zoom = min_zoom
        self._max_zoom = max_zoom
        self.pixel_buffer = layer.layer_settings_with_default('tiles', 'pixel_buffer')
        self.tile_buffer = self.pixel_buffer * 8  # EXTENT_RATIO
        self.features_filter = layer.layer_settings_with_default('tiles', 'features_filter')
        self.properties_filter = layer.layer_settings_with_default('tiles', 'properties_filter')
        self.features_limit = layer.layer_settings_with_default('tiles', 'features_limit')

    def get_id(self):
        return self._name

    def get_description(self):
        return self._description if self._description else self._name.title()

    def get_min_zoom(self):
        if self._min_zoom is not None:
            return self._min_zoom
        return self.layer.layer_settings_with_default('tiles', 'minzoom')

    def get_max_zoom(self):
        if self._max_zoom is not None:
            return self._max_zoom
        return self.layer.layer_settings_with_default('tiles', 'maxzoom')

    def get_queryset(self):
        return self.layer.features.all()

    def get_vector_tile_queryset(self, z=None, x=None, y=None):
        qs = self.get_queryset()
        if self.features_filter is not None:
            qs = qs.filter(properties__contains=self.features_filter)
        if self.features_pk is not None:
            qs = qs.filter(pk__in=list(self.features_pk))
        return qs

    def get_tile_fields(self):
        if self.properties_filter is not None:
            return tuple(f'properties__{f}' for f in self.properties_filter) + ('identifier',)
        return ('properties', 'identifier')

    def get_queryset_limit(self):
        return self.features_limit

    def get_layer_fields(self):
        if not self._include_fields:
            return {}
        properties_filter = self.layer.layer_settings_with_default(
            'tiles', 'properties_filter')
        if properties_filter is not None:
            fields = properties_filter
        elif hasattr(self.layer, 'layer_properties'):
            fields = self.layer.layer_properties.keys()
        else:
            fields = []
        return {f: '' for f in fields}

    def get_tile_cache_key(self, x, y, z):
        if self._cache_key:
            cache_key = self._cache_key
        else:
            cache_key = self.layer.pk

        features_filter_hash = ''
        if self.features_filter is not None:
            features_filter_hash = str(self.features_filter)

        properties_filter_hash = ''
        if self.properties_filter is not None:
            properties_filter_hash = ','.join(self.properties_filter)

        return sha224(
            f'tile_cache_{cache_key}_{x}_{y}_{z}'
            f'_{self.pixel_buffer}_{features_filter_hash}_{properties_filter_hash}'
            f'_{self.features_limit}'.encode()
        ).hexdigest()

    @cached_tile
    def get_tile(self, x, y, z):
        return super().get_tile(x, y, z)


class VectorTile(object):
    """Legacy wrapper kept for backward compatibility"""
    def __init__(self, layer, cache_key=None):
        self.layer, self.cache_key = layer, cache_key
        self.pixel_buffer = self.layer.layer_settings_with_default('tiles', 'pixel_buffer')
        self.features_filter = self.layer.layer_settings_with_default('tiles', 'features_filter')
        self.properties_filter = self.layer.layer_settings_with_default('tiles', 'properties_filter')
        self.features_limit = self.layer.layer_settings_with_default('tiles', 'features_limit')

    # Number of tile units per pixel
    EXTENT_RATIO = 8
    TILE_WIDTH_PIXEL = 512

    def get_tile(self, x, y, z, name=None, features_pks=None):
        vector_layer = GeoStoreVectorLayer(
            self.layer, name=name, features_pk=features_pks, cache_key=self.cache_key
        )
        tile = vector_layer.get_tile(x, y, z)
        return tile

    def get_tile_cache_key(self, x, y, z):
        if self.cache_key:
            cache_key = self.cache_key
        else:
            cache_key = self.layer.pk

        features_filter_hash = ''
        if self.features_filter is not None:
            features_filter_hash = str(self.features_filter)

        properties_filter_hash = ''
        if self.properties_filter is not None:
            properties_filter_hash = ','.join(self.properties_filter)

        return sha224(
            f'tile_cache_{cache_key}_{x}_{y}_{z}'
            f'_{self.pixel_buffer}_{features_filter_hash}_{properties_filter_hash}'
            f'_{self.features_limit}'.encode()
        ).hexdigest()


def guess_maxzoom(layer):
    features = layer.features.all()
    layer_query = features.annotate(
        geom3857=Transform('geom', EPSG_3857)
    )

    layer_raw_query, args = layer_query.query.sql_with_params()

    try:
        with connection.cursor() as cursor:
            sql_query = f'''
                WITH
                q1 AS ({layer_raw_query}),
                q2 AS (SELECT ST_X((ST_DumpPoints(geom3857)).geom) AS x FROM q1),
                q3 AS (SELECT x - lag(x) OVER (ORDER BY x) AS dst FROM q2),
                q4 AS (SELECT * FROM q3 WHERE dst > 0)
                SELECT
                    exp(sum(ln(dst))/count(dst)) AS avg
                FROM
                    q4
                '''
            cursor.execute(sql_query, args)
            row = cursor.fetchone()

        # geometric mean of the |x_{i+1}-x_i| for all points (x,y) in layer.pk
        avg = row[0]

        # total number of pixels to represent length `avg` (equator)
        nb_pixels_total = 2 * pi * EARTH_RADIUS / avg

        tile_resolution = VectorTile.TILE_WIDTH_PIXEL * VectorTile.EXTENT_RATIO

        # zoom (ceil) to fit those pixels at `tile_resolution`
        max_zoom = ceil(log(nb_pixels_total / tile_resolution, 2))

        return min(max_zoom, 22)
    except TypeError:
        return 14  # Arbitrary zoom value


def guess_minzoom(layer):
    """
    Procedure that uses DB output to guess a min zoom level.

    Criteria: zoom satisfying the following condition:
    tile_lenght / tile_fraction <= BBox(features).smallerSide
    If extent = 0, returns 0

    Explanation about the tile_fraction = 8 just above:
    ---------------------------------------------------
    It's purpose is to give an idea of when a dataset becomes to small
    to be shown in the map, so when doing.
    """

    extent = SIGTools.get_extent_of_layer(layer)

    if extent == 0:
        return 0

    tile_fraction = 8
    min_zoom = floor(log((2 * pi * EARTH_RADIUS) / (extent * tile_fraction), 2))
    return min(min_zoom, 22)
