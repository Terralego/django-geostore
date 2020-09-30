from django.conf import settings
from django.contrib.gis.geos import GeometryCollection, Point, LineString, Polygon
from rest_framework.utils.serializer_helpers import ReturnDict

from geostore.models import Feature
from rest_framework.renderers import JSONRenderer, BaseRenderer
from rest_framework_xml.renderers import XMLRenderer
import simplekml
import gpxpy.gpx


class GeoJSONRenderer(JSONRenderer):
    """
    GeoJSON renderer is just used to match with geojson format.
    Serializer is adapted along this format with djangorestframework-gis
    """
    format = 'geojson'


class KMLRenderer(BaseRenderer):
    format = 'kml'
    media_type = 'application/vnd.google-earth.kml+xml'
    name_tag = 'identifier'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kml = simplekml.Kml()

    def render_line(self, kml, name, line_geom):
        kml.newlinestring(name=name, coords=line_geom.coords)

    def get_element_infos(self, element):
        description = ""
        for key, value in element.get('properties').items():
            description += f"{key}: {value}\n"
        return (
            element.get('geom').get('type').lower(),
            element.get('identifier'),
            element.get('geom').get('coordinates'),
            description
        )

    def parse_element(self, element):
        geom_type, identifier, coordinates, description = self.get_element_infos(element)

        if geom_type == 'point':
            self.kml.newpoint(name=identifier, description=description, coords=coordinates)
        elif geom_type == 'linestring':
            self.kml.newlinestring(name=identifier, description=description, coords=coordinates)
        elif geom_type == 'polygon':
            self.kml.newpolygon(name=identifier, description=description, coords=coordinates)
        else:
            multi = self.kml.newmultigeometry(name=identifier, description=description)
            if geom_type == 'multipoint':
                for point in coordinates:
                    multi.newpoint(coords=point)
            elif geom_type == 'multilinestring':
                for line in coordinates:
                    multi.newlinestring(coords=line)
            elif geom_type == 'multipolygon':
                for polygon in coordinates:
                    multi.newpolygon(coords=polygon)

        return self.kml.kml()

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, ReturnDict):
            # simple object serialization
            self.parse_element(data)

        else:
            # object list serialization
            for element in data:
                self.parse_element(element)

        return self.kml.kml()


class GPXRenderer(XMLRenderer):
    format = 'gpx'
    media_type = 'application/gpx+xml'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gpx = gpxpy.gpx.GPX()

    def render(self, data, accepted_media_type=None, renderer_context=None):
        feat = Feature.objects.get(identifier=data.get('identifier'))
        return self.geom_to_gpx(feat.geom, feat.identifier, "")

    def _point_to_gpx(self, point, klass=gpxpy.gpx.GPXWaypoint):
        if isinstance(point, (tuple, list)):
            point = Point(*point, srid=settings.INTERNAL_GEOMETRY_SRID)
        newpoint = point.transform(4326, clone=True)  # transformation: gps uses 4326
        # transform looses the Z parameter
        return klass(latitude=newpoint.y, longitude=newpoint.x, elevation=point.z)

    def geom_to_gpx(self, geom, name, description):
        """Convert a geometry to a gpx entity.
        Raise ValueError if it is not a Point, LineString or a collection of those
        Point -> add as a Way Point
        LineString -> add all Points in a Route
        Polygon -> add all Points of the external linering in a Route
        Collection (of LineString or Point) -> add as a route, concatening all points
        """
        if isinstance(geom, GeometryCollection):
            for i, g in enumerate(geom):
                self.geom_to_gpx(g, "%s (%s)" % (name, i), description)
        elif isinstance(geom, Point):
            wp = self._point_to_gpx(geom)
            wp.name = name
            wp.description = description
            self.gpx.waypoints.append(wp)
        elif isinstance(geom, LineString):
            gpx_track = gpxpy.gpx.GPXTrack(name=name, description=description)
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_segment.points = [self._point_to_gpx(point, klass=gpxpy.gpx.GPXTrackPoint) for point in geom]
            gpx_track.segments.append(gpx_segment)
            self.gpx.tracks.append(gpx_track)
        elif isinstance(geom, Polygon):
            self.geom_to_gpx(geom[0], name, description)
        else:
            raise ValueError("Unsupported geometry %s" % geom)
        return self.gpx.to_xml()
