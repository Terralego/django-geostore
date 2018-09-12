import mercantile
from django.contrib.gis.geos import GEOSGeometry, MultiLineString
from django.core.cache import cache
from django.db import connection
from django.db.models import F, Value

from .funcs import (ST_AsMvtGeom, ST_Distance, ST_LineLocatePoint,
                    ST_LineSubstring, ST_MakeEnvelope, ST_Transform)

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
    def __init__(self, layer):
        self.layer = layer

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

        mvt_query = features.model.objects.raw(
            f'''
            WITH tilegeom as ({layer_raw_query})
            SELECT %s AS id, count(*) AS count,
                   ST_AsMVT(tilegeom, %s, 4096, 'geometry') AS mvt
            FROM tilegeom
            ''',
            args + (self.layer.pk, self.layer.name)
        )[0]

        return (mvt_query.count, mvt_query.mvt)

    def get_tile_cache_key(self, x, y, z):
        return f'tile_cache_{self.layer.pk}_{x}_{y}_{z}'

    def clean_tiles(self, tiles):
        return cache.delete_many(
            [self.get_tile_cache_key(*tile) for tile in tiles])


class Routing(object):

    def __init__(self, points, layer):
        self.points, self.layer = points, layer

    def get_route(self):
        '''Return the geometry of the route from the given points'''
        self.points = self._get_points_in_lines()
        routes = self._points_route()
        if routes:
            return self._merge_routes(routes)

    @classmethod
    def create_topology(cls, layer):
        cursor = connection.cursor()
        raw_query = """
                    SELECT
                        pgr_createTopology(
                            %s,
                            0.00000000000001,
                            'geom',
                            'id',
                            'source',
                            'target',
                            'layer_id = %s',
                            clean := TRUE)
                    """

        cursor.execute(raw_query,
                       [layer.features.model._meta.db_table, layer.pk])
        return ('OK',) == cursor.fetchone()

    def _merge_routes(self, routes):
        linestrings = []

        # MultiLineStrings must be splitted in LineString objects
        for route in routes:
            if isinstance(route, MultiLineString):
                for line in route:
                    linestrings.append(line)
            else:
                linestrings.append(route)

        return MultiLineString(*linestrings).merged

    def _get_points_in_lines(self):
        '''Returns position of the point in the closed geometry'''
        snapped_points = []

        for point in self.points:
            closest_feature = self._get_closest_geometry(point)

            snapped_points.append(
                self._snap_point_on_feature(point, closest_feature))

        return snapped_points

    def _get_closest_geometry(self, point):
        return self.layer.features.all().annotate(
                distance=ST_Distance(F('geom'), Value(str(point)))
            ).order_by('distance').first()

    def _snap_point_on_feature(self, point, feature):
        return self.layer.features.annotate(
            fraction=ST_LineLocatePoint(F('geom'), Value(str(point))),
        ).get(pk=feature.pk)

    def _points_route(self):
        route = []
        for index, point in enumerate(self.points):
            try:
                next_point = self.points[index + 1]

                # If both points are on same edge we do not need pgRouting
                # just split the edge from point to point.
                if point.pk == next_point.pk:
                    route.append(
                        self._get_line_substring(point,
                                                 [point.fraction,
                                                  next_point.fraction]))
                else:
                    raw_route = self._get_raw_route(point, next_point)
                    if raw_route:
                        route.append(raw_route)

            except IndexError:
                break
        return route

    def _get_line_substring(self, feature, fractions):
        splitted = self.layer.features.annotate(
                        splitted_geom=ST_LineSubstring(F('geom'),
                                                       float(min(fractions)),
                                                       float(max(fractions)))
                   ).get(pk=feature.pk)

        return splitted.splitted_geom

    def _get_raw_route(self, start_point, end_point):
            """Return raw route between two points from pgrouting's
            pgr_withPoints function that need to be transformed to
            real geometry
            The result of pgr_withPoints() looks like this, the result is not
            edges but nodes. The reconstitution must be based on this.
            p(-1)---node(1)---node(2)---node(3)...node(20)---node(21)---p(-2)
            """

            q = """
            WITH points AS (
                -- This is a virtual table of points used for routing and
                -- their position on the closest edge.
                SELECT *,
                    ST_Line_Interpolate_Point(
                        terra_feature.geom, fraction) AS point_geom,
                    ST_Split(
                        ST_Snap(
                            terra_feature.geom,
                            ST_Line_Interpolate_Point(
                                terra_feature.geom,
                                fraction),
                            0.00001),
                            -- This tolerance seems to be enought, maybe it
                            -- can be improved or come from a setting.
                            -- It could depend of the topology and the
                            -- precision of the geometries in the layer.
                        ST_Line_Interpolate_Point(
                            terra_feature.geom, fraction)
                    ) AS point_geoms
                FROM (VALUES (1, %s, %s::float), (2, %s, %s::float))
                    AS points (pid, edge_id, fraction)
                LEFT OUTER JOIN terra_feature ON edge_id = terra_feature.id
            ),
            pgr AS (
                -- Here we do the routing from point 1 to point 2 using
                -- pgr_withPoints that uses the dijkstra algorythm. prev_geom
                -- and next_geom are used later to reconstruct the final
                -- geometry of the shortest path.
                SELECT
                    pgr.*,
                    points.*,
                    terra_feature.geom AS edge_geom,
                    (LAG(terra_feature.geom, 2) OVER (ORDER BY path_seq))
                        AS prev_geom,
                    (LEAD(terra_feature.geom) OVER (ORDER BY path_seq))
                        AS next_geom
                FROM
                    pgr_withPoints(
                        'SELECT id, source, target,
                            ST_Length(geom) AS cost,
                            ST_Length(geom) AS reverse_cost
                         FROM terra_feature
                         WHERE layer_id = %s
                               AND source IS NOT NULL
                         ORDER BY id',
                        'SELECT *
                         FROM (VALUES (1, %s, %s::float), (2, %s, %s::float))
                            AS points (pid, edge_id, fraction)',
                        -1, -2, details := true
                    ) AS pgr
                LEFT OUTER JOIN terra_feature ON pgr.edge = terra_feature.id
                LEFT OUTER JOIN points ON points.pid = -node
            ),
            route AS (
                /* Finaly we reconstruct the geometry. Each edge, where the
                   point 1 and 2 are, are splitted on the point, and here we
                   find the closest part of the next edge for the first point
                   and the previous edge for the last point. Then
                   we merge all segments.
                */
                SELECT
                    *,
                    (
                        CASE
                        WHEN (LEAD(edge) OVER (ORDER BY path_seq)) = -1 THEN
                        (
                            /* Skip before last sequence that is useless.
                               Why is it useless? Seems to be a pgrouting bug.
                               In fact, the before last geometry is the edge
                               where the last points it places, if we keep it,
                               the final LineString go too far from the point.
                            */
                            ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 4326)
                        )
                        WHEN edge = -1 THEN
                        (
                            /* Select from n-1 to previous vertice substring
                               This is used to find the closest edge of the
                               last point in the route.
                            */
                            SELECT
                                geom
                            FROM (
                                SELECT (ST_Dump(point_geoms)).geom as geom
                            ) AS point_lines
                            ORDER BY ST_Distance(geom, prev_geom) ASC
                            LIMIT 1
                        )
                        WHEN node < 0 THEN
                        (
                            -- Same as previously but for next_geometry
                            SELECT
                                geom
                            FROM (
                                SELECT (ST_Dump(point_geoms)).geom as geom
                            ) AS point_lines
                            ORDER BY ST_Distance(geom, next_geom) ASC
                            LIMIT 1
                        )
                        ELSE
                            -- It's an edge, so let's return the full edge
                            -- geometry
                            edge_geom
                        END
                    ) AS final_geometry
                FROM pgr
            )
            SELECT ST_LineMerge(ST_Multi(ST_Collect(final_geometry)))
                   AS geometry
            FROM route;
            """

            with connection.cursor() as cursor:
                cursor.execute(q, [
                                   start_point.pk, float(start_point.fraction),
                                   end_point.pk, float(end_point.fraction),
                                   self.layer.pk,
                                   start_point.pk, float(start_point.fraction),
                                   end_point.pk, float(end_point.fraction),
                                   ])
                return GEOSGeometry(cursor.fetchone()[0])

            return None
