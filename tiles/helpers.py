import hashlib
from math import ceil, log, pi

import mercantile
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import F

from .funcs import (ST_Area, ST_Length, ST_MakeEnvelope, ST_SnapToGrid,
                    ST_Transform)

EPSG_3857 = 3857
EARTH_RADIUS = 6371008


def cached_tile(func, expiration=3600*24):
    def wrapper(self, x, y, z,
                pixel_buffer, features_filter, properties_filter,
                features_limit, *args, **kwargs):
        cache_key = self.get_tile_cache_key(
            x, y, z,
            pixel_buffer, features_filter, properties_filter,
            features_limit)

        def build_tile():
            (a, b) = func(
                self, x, y, z,
                pixel_buffer, features_filter, properties_filter,
                features_limit, *args, **kwargs)
            return (a, b.tobytes())
        return cache.get_or_set(cache_key, build_tile, expiration)
    return wrapper


class VectorTile(object):
    def __init__(self, layer, cache_key=None):
        self.layer, self.cache_key = layer, cache_key

    # Number of tile units per pixel
    EXTENT_RATIO = 16

    LINESTRING = ('LineString', 'MultiLineString')
    POLYGON = ('Polygon', 'MultiPolygon')

    @cached_tile
    def get_tile(self, x, y, z,
                 pixel_buffer, features_filter, properties_filter,
                 features_limit, features):

        bounds = mercantile.bounds(x, y, z)
        self.xmin, self.ymin = mercantile.xy(bounds.west, bounds.south)
        self.xmax, self.ymax = mercantile.xy(bounds.east, bounds.north)
        pixel_width_x = (self.xmax - self.xmin) / 256
        pixel_width_y = (self.ymax - self.ymin) / 256

        layer_query = features.annotate(
                bbox=ST_MakeEnvelope(
                    self.xmin,
                    self.ymin,
                    self.xmax,
                    self.ymax,
                    EPSG_3857),
                # Intersects on internal data projection using pixel buffer
                bbox_select=ST_Transform(ST_MakeEnvelope(
                    self.xmin - pixel_width_x * pixel_buffer,
                    self.ymin - pixel_width_y * pixel_buffer,
                    self.xmax + pixel_width_x * pixel_buffer,
                    self.ymax + pixel_width_y * pixel_buffer,
                    EPSG_3857), settings.INTERNAL_GEOMETRY_SRID),
                geom3857=ST_Transform('geom', EPSG_3857),
                geom3857snap=ST_SnapToGrid(
                    'geom3857',
                    pixel_width_x / self.EXTENT_RATIO,
                    pixel_width_y / self.EXTENT_RATIO)
            ).filter(
                bbox_select__intersects=F('geom'),
                geom3857snap__isnull=False
            )

        if features_filter is not None:
            layer_query = layer_query.filter(
                properties__contains=features_filter
            )

        if self.layer.layer_geometry in self.LINESTRING:
            # Larger then a half of pixel
            layer_query = layer_query.annotate(
                length3857=ST_Length('geom3857snap')
            ).filter(
                length3857__gt=(pixel_width_x + pixel_width_y) / 2 / 2
            )
        elif self.layer.layer_geometry in self.POLYGON:
            # Larger than a quarter of pixel
            layer_query = layer_query.annotate(
                area3857=ST_Area('geom3857snap')
            ).filter(
                area3857__ge=pixel_width_x * pixel_width_y / 4
            )

        if features_limit is not None:
            # Order by feature size before limit
            if self.layer.layer_geometry in self.LINESTRING:
                layer_query = layer_query.order_by('length3857')
            elif self.layer.layer_geometry in self.POLYGON:
                layer_query = layer_query.order_by('area3857')

            layer_query = layer_query[:features_limit]

        layer_raw_query, args = layer_query.query.sql_with_params()

        filter = 'ARRAY[]::text[]'
        if properties_filter is not None:
            filter = ', '.join([f"'{f}'" for f in properties_filter])
            filter = f'''
                SELECT array_agg(k)
                FROM jsonb_object_keys(properties) AS t(k)
                WHERE k NOT IN ({filter})'''
        with connection.cursor() as cursor:
            sql_query = f'''
                WITH
                fullgeom AS ({layer_raw_query}),
                tilegeom AS (
                    SELECT
                        properties - ({filter}) AS properties,
                        ST_AsMvtGeom(
                            geom3857snap,
                            bbox,
                            {256 * self.EXTENT_RATIO},
                            {pixel_buffer * self.EXTENT_RATIO},
                            true) AS geometry
                    FROM
                        fullgeom)
                SELECT
                    count(*) AS count,
                    ST_AsMVT(
                        tilegeom,
                        CAST(%s AS text),
                        {256 * self.EXTENT_RATIO},
                        'geometry'
                    ) AS mvt
                FROM
                    tilegeom
            '''

            cursor.execute(sql_query, args + (self.layer.name, ))
            row = cursor.fetchone()

            return row[0], row[1]

    def get_tile_cache_key(self, x, y, z,
                           pixel_buffer, features_filter, properties_filter,
                           features_limit):
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
        if properties_filter is not None:
            properties_filter_hash = \
                hashlib.sha224(
                    ','.join(properties_filter).encode('utf-8')
                ).hexdigest()
        return (
            f'tile_cache_{cache_key}_{x}_{y}_{z}'
            f'_{pixel_buffer}_{features_filter_hash}_{properties_filter_hash}'
            f'_{features_limit}'
        )

    def clean_tiles(self, tiles, pixel_buffer, features_filter,
                    properties_filter, features_limit):
        return cache.delete_many([
            self.get_tile_cache_key(
                *tile, pixel_buffer, features_filter, properties_filter,
                features_limit)
            for tile in tiles
        ])


def guess_minzoom(layer):
    return 0


def guess_maxzoom(layer):
    # TODO: layer_query=layer_query[:features_limit] -> set limit?

    max_zoom = int(22)

    features = layer.features.all()
    layer_query = features.annotate(
        geom3857=ST_Transform('geom', EPSG_3857)
        )

    layer_raw_query, args = layer_query.query.sql_with_params()

    try:
        avg_query = features.model.objects.raw(
            f'''
            WITH q1 AS
            (SELECT * FROM ({layer_raw_query}) as foo),
            q2 AS
            (select ST_X((ST_DumpPoints(geom)).geom) AS x from q1 order by x),
            q3 AS
            (select x - lag(x) over () AS dst from q2),
            q4 AS
            (SELECT * FROM q3 WHERE dst > 0)
            select  %s AS id, CAST(%s AS text) AS layer_name,
            exp( sum(ln(dst))/count(dst) ) AS avg
            FROM q4
            ''', args + (layer.pk, layer.name)
        )[0]

        # geometric mean of the |x_{i+1}-x_i| for all points (x,y) in layer.pk
        avg = avg_query.avg

        # zoom (ceil(zoom)) corresponding to this distance
        max_zoom = ceil(log((2*pi*EARTH_RADIUS/avg), 2))

    except TypeError:
        return -1

    return max_zoom
