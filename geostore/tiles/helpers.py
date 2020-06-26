import hashlib
from random import uniform

import mercantile
from django.core.cache import cache
from django.db import connection
from django.db.models import F
from math import ceil, floor, log, pi

from . import EARTH_RADIUS, EPSG_3857
from .funcs import (ST_Area, ST_Length, ST_MakeEnvelope,
                    ST_SimplifyPreserveTopology, ST_Transform)
from .sigtools import SIGTools
from .. import settings as app_settings


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
            (a, b) = func(
                self, x, y, z, *args, **kwargs)
            return a, b.tobytes()

        return cache.get_or_set(cache_key, build_tile, expiration, version=version)

    return wrapper


class VectorTile(object):
    def __init__(self, layer, cache_key=None):
        self.layer, self.cache_key = layer, cache_key
        self.pixel_buffer = self.layer.layer_settings_with_default('tiles', 'pixel_buffer')
        self.features_filter = self.layer.layer_settings_with_default('tiles', 'features_filter')
        self.properties_filter = self.layer.layer_settings_with_default('tiles', 'properties_filter')
        self.features_limit = self.layer.layer_settings_with_default('tiles', 'features_limit')

    # Number of tile units per pixel
    EXTENT_RATIO = 8
    TILE_WIDTH_PIXEL = 512

    def _simplify(self, layer_query, pixel_width_x, pixel_width_y):
        if self.layer.is_polygon:
            # Grid step is pixel_width_x / EXTENT_RATIO and pixel_width_y / EXTENT_RATIO
            # Simplify to average half pixel width
            layer_query = layer_query.annotate(
                outgeom3857=ST_SimplifyPreserveTopology('outgeom3857', (pixel_width_x + pixel_width_y) / 2 / 2)
            )
        return layer_query

    def _filter_on_property(self, layer_query, features_filter):
        if features_filter is not None:
            layer_query = layer_query.filter(
                properties__contains=features_filter
            )
        return layer_query

    def _filter_on_geom_size(self, layer_query, layer_geometry, pixel_width_x, pixel_width_y):
        if self.layer.is_linestring:
            # Larger then a half of pixel
            layer_query = layer_query.annotate(
                length3857=ST_Length('outgeom3857')
            ).filter(
                length3857__gt=(pixel_width_x + pixel_width_y) / 2 / 2
            )
        elif self.layer.is_polygon:
            # Larger than a quarter of pixel
            layer_query = layer_query.annotate(
                area3857=ST_Area('outgeom3857')
            ).filter(
                area3857__gt=pixel_width_x * pixel_width_y / 4
            )
        return layer_query

    def _limit(self, layer_query, features_limit):
        if features_limit is not None:
            # Order by feature size before limit
            if self.layer.is_linestring:
                layer_query = layer_query.order_by('length3857')
            elif self.layer.is_polygon:
                layer_query = layer_query.order_by('area3857')

            layer_query = layer_query[:features_limit]
        return layer_query

    def get_tile_bbox(self, x, y, z):
        bounds = mercantile.bounds(x, y, z)
        return (*mercantile.xy(bounds.west, bounds.south), *mercantile.xy(bounds.east, bounds.north))

    def pixel_widths(self, xmin, ymin, xmax, ymax):
        return (
            (xmax - xmin) / self.TILE_WIDTH_PIXEL,
            (ymax - ymin) / self.TILE_WIDTH_PIXEL
        )

    @cached_tile
    def get_tile(self, x, y, z):
        xmin, ymin, xmax, ymax = self.get_tile_bbox(x, y, z)
        pixel_width_x, pixel_width_y = self.pixel_widths(xmin, ymin, xmax, ymax)

        layer_query = self.layer.features.annotate(
            bbox=ST_MakeEnvelope(
                xmin,
                ymin,
                xmax,
                ymax,
                EPSG_3857),
            # Intersects on internal data projection using pixel buffer
            bbox_select=ST_Transform(ST_MakeEnvelope(
                xmin - pixel_width_x * self.pixel_buffer,
                ymin - pixel_width_y * self.pixel_buffer,
                xmax + pixel_width_x * self.pixel_buffer,
                ymax + pixel_width_y * self.pixel_buffer,
                EPSG_3857), app_settings.INTERNAL_GEOMETRY_SRID),
            outgeom3857=ST_Transform('geom', EPSG_3857),
        ).filter(
            bbox_select__intersects=F('geom')
        )

        # Filter features
        layer_query = self._filter_on_property(layer_query, self.features_filter)
        layer_query = self._filter_on_geom_size(layer_query, self.layer.layer_geometry, pixel_width_x, pixel_width_y)

        # Lighten geometry
        layer_query = self._simplify(layer_query, pixel_width_x, pixel_width_y)

        # Seatbelt
        layer_query = self._limit(layer_query, self.features_limit)

        layer_raw_query, args = layer_query.query.sql_with_params()

        if self.properties_filter:
            filter = ', '.join([f"'{f}'" for f in self.properties_filter])
            properties = f'''
                (
                    SELECT jsonb_object_agg(key, value) FROM
                    jsonb_each(properties)
                    WHERE key IN ({filter})
                )
                '''
        elif self.properties_filter == []:
            properties = "'{}'::jsonb"
        else:
            properties = "properties"

        properties += " || json_build_object('_id', identifier)::jsonb"

        with connection.cursor() as cursor:
            sql_query = f'''
                WITH
                fullgeom AS ({layer_raw_query}),
                tilegeom AS (
                    SELECT
                        ({properties}) AS properties,
                        ST_AsMvtGeom(
                            outgeom3857,
                            bbox,
                            {self.TILE_WIDTH_PIXEL * self.EXTENT_RATIO},
                            {self.pixel_buffer * self.EXTENT_RATIO},
                            true) AS geometry
                    FROM
                        fullgeom)
                SELECT
                    count(*) AS count,
                    ST_AsMVT(
                        tilegeom,
                        CAST(%s AS text),
                        {self.TILE_WIDTH_PIXEL * self.EXTENT_RATIO},
                        'geometry'
                    ) AS mvt
                FROM
                    tilegeom
            '''

            cursor.execute(sql_query, args + (self.layer.name,))
            row = cursor.fetchone()

            return row[0], row[1]

    def get_tile_cache_key(self, x, y, z):
        if self.cache_key:
            cache_key = self.cache_key
        else:
            cache_key = self.layer.pk

        features_filter = ''
        if features_filter is not None:
            features_filter_hash = \
                hashlib.sha224(
                    str(features_filter).encode('utf-8')
                ).hexdigest()
        properties_filter_hash = ''
        if self.properties_filter is not None:
            properties_filter_hash = \
                hashlib.sha224(
                    ','.join(self.properties_filter).encode('utf-8')
                ).hexdigest()
        return (
            f'tile_cache_{cache_key}_{x}_{y}_{z}'
            f'_{self.pixel_buffer}_{features_filter_hash}_{properties_filter_hash}'
            f'_{self.features_limit}'
        )


def guess_maxzoom(layer):
    features = layer.features.all()
    layer_query = features.annotate(
        geom3857=ST_Transform('geom', EPSG_3857)
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
