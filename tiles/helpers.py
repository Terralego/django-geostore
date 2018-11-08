import mercantile
from django.core.cache import cache
from django.db import connection
from django.db.models import F

from .funcs import ST_AsMvtGeom, ST_MakeEnvelope, ST_Transform

EPSG_3857 = 3857


def cached_tile(func, expiration=3600*24):
    def wrapper(self, x, y, z, *args, **kwargs):
        cache_key = self.get_tile_cache_key(x, y, z)

        def build_tile():
            (a, b) = func(self, x, y, z, *args, **kwargs)
            return (a, b.tobytes())
        return cache.get_or_set(cache_key, build_tile, expiration)
    return wrapper


class VectorTile(object):
    def __init__(self, layer, cache_key=None):
        self.layer, self.cache_key = layer, cache_key

    @cached_tile
    def get_tile(self, x, y, z, features):

        bounds = mercantile.bounds(x, y, z)
        self.xmin, self.ymin = mercantile.xy(bounds.west, bounds.south)
        self.xmax, self.ymax = mercantile.xy(bounds.east, bounds.north)

        layer_query = features.annotate(
                bbox=ST_MakeEnvelope(self.xmin,
                                     self.ymin,
                                     self.xmax,
                                     self.ymax,
                                     EPSG_3857),
                geom3857=ST_Transform('geom', EPSG_3857)
            ).filter(
                bbox__intersects=F('geom3857')
            ).annotate(
                geometry=ST_AsMvtGeom(
                    F('geom3857'),
                    'bbox',
                    4096,
                    256,
                    True
                )
            )
        layer_raw_query, args = layer_query.query.sql_with_params()

        with connection.cursor() as cursor:
            sql_query = f'''
                WITH tilegeom as ({layer_raw_query})
                   SELECT count(*) AS count,
                          ST_AsMVT(tilegeom,
                                   '{self.layer.name}',
                                   4096, 'geometry') AS mvt
                   FROM tilegeom
            '''

            cursor.execute(sql_query, args)
            row = cursor.fetchone()

            return row[0], row[1]

    def get_tile_cache_key(self, x, y, z):
        if self.cache_key:
            cache_key = self.cache_key
        else:
            cache_key = self.layer.pk
        return f'tile_cache_{cache_key}_{x}_{y}_{z}'

    def clean_tiles(self, tiles):
        return cache.delete_many(
            [self.get_tile_cache_key(*tile) for tile in tiles])
