import hashlib

import mercantile
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import F

from .funcs import ST_AsMvtGeom, ST_MakeEnvelope, ST_SnapToGrid, ST_Transform

EPSG_3857 = 3857


def cached_tile(func, expiration=3600*24):
    def wrapper(self, x, y, z, pixel_buffer, properties_filter, *args,
                **kwargs):
        cache_key = self.get_tile_cache_key(x, y, z, pixel_buffer,
                                            properties_filter)

        def build_tile():
            (a, b) = func(self, x, y, z, pixel_buffer, properties_filter,
                          *args, **kwargs)
            return (a, b.tobytes())
        return cache.get_or_set(cache_key, build_tile, expiration)
    return wrapper


class VectorTile(object):
    def __init__(self, layer, cache_key=None):
        self.layer, self.cache_key = layer, cache_key

    # Number of tile units per pixel
    EXTENT_RATIO = 16

    @cached_tile
    def get_tile(self, x, y, z, pixel_buffer, properties_filter, features):

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
            ).annotate(
                geometry=ST_AsMvtGeom(
                    F('geom3857snap'),
                    'bbox',
                    256 * self.EXTENT_RATIO,
                    pixel_buffer * self.EXTENT_RATIO,
                    True
                )
            )
        layer_raw_query, args = layer_query.query.sql_with_params()

        filter = 'ARRAY[]::text[]'
        if properties_filter is not None:
            filter = '\'' + '\', \''.join(properties_filter) + '\''
            filter = f'''
                SELECT array_agg(k)
                FROM jsonb_object_keys(properties) AS t(k)
                WHERE k NOT IN ({filter})'''
        with connection.cursor() as cursor:
            sql_query = f'''
                WITH tilegeom as ({layer_raw_query})
                SELECT
                    count(*) AS count,
                    ST_AsMVT(
                        tilegeom,
                        CAST(%s AS text),
                        256 * {self.EXTENT_RATIO},
                        'geometry'
                    ) AS mvt
                FROM (
                    SELECT
                        geometry,
                        properties - ({filter}) AS properties
                    FROM tilegeom) AS tilegeom
            '''

            cursor.execute(sql_query, args + (self.layer.name, ))
            row = cursor.fetchone()

            return row[0], row[1]

    def get_tile_cache_key(self, x, y, z, pixel_buffer, properties_filter):
        if self.cache_key:
            cache_key = self.cache_key
        else:
            cache_key = self.layer.pk
        properties_filter_hash = ''
        if properties_filter is not None:
            properties_filter_hash = \
                hashlib.sha224(','.join(properties_filter)).hexdigest()
        return (
            f'tile_cache_{cache_key}_{x}_{y}_{z}_'
            f'{pixel_buffer}_{properties_filter_hash}'
        )

    def clean_tiles(self, tiles, pixel_buffer, properties_filter):
        return cache.delete_many([
            self.get_tile_cache_key(*tile, pixel_buffer, properties_filter)
            for tile in tiles
        ])
