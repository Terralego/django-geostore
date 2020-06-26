import json

from django.contrib.gis.geos import GEOSGeometry, MultiLineString, LineString
from django.core.cache import cache
from django.db import connection
from django.db.models import F, Value

from ..tiles.funcs import ST_Distance, ST_LineLocatePoint, ST_LineSubstring


def cached_segment(func, expiration=3600 * 24):
    def wrapper(self, from_point, to_point, *args, **kwargs):
        cache_key = (f'route_{self.layer.pk}'
                     f'_segment_{from_point.pk}_{from_point.fraction}'
                     f'_{to_point.pk}_{to_point.fraction}')

        def build_segment():
            return func(self, from_point, to_point, *args, **kwargs)

        return cache.get_or_set(cache_key, build_segment, expiration)

    return wrapper


class Routing(object):

    def __init__(self, points, layer):
        if not layer.is_linestring or layer.is_multi:
            raise ValueError('Layer is not routable')

        self.layer = layer
        self.points = self._get_points_in_lines(points)
        self.routes = self._points_route()

    def get_route(self):
        """ Return the geometry of the route from the given points """

        if self.routes:
            return self._serialize_routes(self.routes)

    def get_linestring(self):
        if self.routes:
            way = MultiLineString(*[GEOSGeometry(route['geometry'])
                                    for route in self.routes if isinstance(GEOSGeometry(route['geometry']),
                                                                           LineString)])
            return way.merged

    @classmethod
    def create_topology(cls, layer, tolerance=0.00001, clean=False):
        cursor = connection.cursor()
        raw_query = """
                    SELECT
                        pgr_createTopology(
                            %s,
                            %s,
                            'geom',
                            'id',
                            'source',
                            'target',
                            rows_where := %s,
                            clean := %s)
                    """

        cursor.execute(raw_query,
                       [layer.features.model._meta.db_table, tolerance, f'layer_id={layer.pk} ', clean])
        return ('OK',) == cursor.fetchone()

    def _serialize_routes(self, routes):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry":
                        json.loads(GEOSGeometry(route['geometry']).geojson),
                    "properties": route['properties'],
                }
                for route in routes
            ]
        }

    def _get_points_in_lines(self, points):
        '''Returns position of the point in the closed geometry'''
        snapped_points = []

        for point in points:
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
            except IndexError:
                break

            segment = self._get_segment(point, next_point)

            if segment:
                route.extend(segment)

        return route

    @cached_segment
    def _get_segment(self, from_point, to_point):
        if from_point.pk == to_point.pk:
            # If both points are on same edge we do not need pgRouting
            # just split the edge from point to point.
            segment = [self._get_line_substring(from_point,
                                                [from_point.fraction,
                                                 to_point.fraction]), ]
        else:
            # Ask pgRouting the route from point to the next point
            segment = self._get_raw_route(from_point, to_point)

        return segment

    def _get_line_substring(self, feature, fractions):
        feature = self.layer.features.annotate(
            splitted_geom=ST_LineSubstring(F('geom'),
                                           float(min(fractions)),
                                           float(max(fractions)))
        ).get(pk=feature.pk)

        return {
            'geometry': feature.splitted_geom,
            'properties': feature.properties,
        }

    def _get_raw_route(self, start_point, end_point):
        """Return raw route between two points from pgrouting's
        pgr_withPoints function that need to be transformed to
        real geometry.
        """

        q = """
        WITH points AS (
            -- This is a virtual table of points used for routing and
            -- their position on the closest edge.
            SELECT
                points.pid,
                points.edge_id,
                ST_LineSubstring(geostore_feature.geom,
                                 points.fraction_start,
                                 points.fraction_end) AS geom
            FROM
                (VALUES
                    (1, %s, 0, %s::float),
                    (1, %s, %s::float, 1),
                    (2, %s, 0, %s::float),
                    (2, %s, %s::float, 1)
                ) AS points(pid, edge_id, fraction_start, fraction_end)
                JOIN geostore_feature ON
                    geostore_feature.id = points.edge_id
        ),
        pgr AS (
            -- Here we do the routing from point 1 to point 2 using
            -- pgr_withPoints that uses the dijkstra algorythm. next_node
            -- and next_geom are used later to reconstruct the final
            -- geometry of the shortest path.
            SELECT
                pgr.path_seq,
                pgr.node,
                pgr.edge,
                geostore_feature.geom AS edge_geom,
                geostore_feature.properties,
                (LEAD(pgr.node) OVER (ORDER BY path_seq))
                    AS next_node,
                (LAG(geostore_feature.geom) OVER (ORDER BY path_seq))
                    AS prev_geom,
                (LEAD(geostore_feature.geom) OVER (ORDER BY path_seq))
                    AS next_geom
            FROM
                pgr_withPoints(
                    'SELECT id, source, target,
                        ST_Length(geom) AS cost,
                        ST_Length(geom) AS reverse_cost
                        FROM geostore_feature
                        WHERE layer_id = %s
                            AND source IS NOT NULL
                        ORDER BY id',
                    'SELECT *
                        FROM (VALUES (1, %s, %s::float), (2, %s, %s::float))
                        AS points (pid, edge_id, fraction)',
                    -1, -2, details := true
                ) AS pgr
            LEFT OUTER JOIN geostore_feature ON pgr.edge = geostore_feature.id
        ),
        route AS (
            /* Finally we reconstruct the geometry by collecting each edge.
                At point 1 and 2, we get the split edge.
            */
            SELECT
                CASE
                WHEN node = -1 THEN  -- Start Point
                    (SELECT points.geom
                        FROM points
                        WHERE points.pid = -pgr.node
                        -- Non topological graph,
                        -- get the closest to the next edge
                        ORDER BY ST_Distance(points.geom, pgr.next_geom) ASC
                        LIMIT 1)
                WHEN next_node = -2 THEN  -- Going to End Point
                    (SELECT points.geom
                        FROM points
                        WHERE points.pid = -pgr.next_node
                        -- Non topologic graph,
                        -- get the closest to the previous egde
                        ORDER BY ST_Distance(points.geom, pgr.prev_geom) ASC
                        LIMIT 1)
                ELSE
                    edge_geom  -- Let's return the full edge geometry
                END AS final_geometry,
                properties
            FROM pgr
        )
        SELECT
            final_geometry AS geometry,
            properties
        FROM route
        WHERE final_geometry IS NOT NULL;
        """
        self._fix_point_fraction(start_point)
        self._fix_point_fraction(end_point)

        with connection.cursor() as cursor:
            cursor.execute(q, [
                start_point.pk, float(start_point.fraction),
                start_point.pk, float(start_point.fraction),
                end_point.pk, float(end_point.fraction),
                end_point.pk, float(end_point.fraction),
                self.layer.pk,
                start_point.pk, float(start_point.fraction),
                end_point.pk, float(end_point.fraction),
            ])

            return [
                {
                    'geometry': geometry,
                    'properties': properties
                } for geometry, properties in cursor.fetchall()
            ]

    def _fix_point_fraction(self, point):
        """ This function is used to fix problem with pgrouting when point
        position on the edge is 0.0 or 1.0, that create a routing topology
        problem. See https://github.com/pgRouting/pgrouting/issues/760
        So we create a fake fraction near the vertices of the edge.
        """
        if float(point.fraction) == 1.0:
            point.fraction = 0.99999
        elif float(point.fraction) == 0.0:
            point.fraction = 0.00001
