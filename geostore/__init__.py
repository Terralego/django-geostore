from django.db.models import IntegerChoices

default_app_config = 'geostore.apps.GeostoreConfig'


class GeometryTypes(IntegerChoices):
    Point = 0, 'Point'
    LineString = 1, 'LineString'
    # LinearRing 2
    Polygon = 3, 'Polygon'
    MultiPoint = 4, 'MultiPoint'
    MultiLineString = 5, 'MultiLineString'
    MultiPolygon = 6, 'MultiPolygon'
    GeometryCollection = 7, 'GeometryCollection'

    @classmethod
    def shape_allowed_types(cls):
        """
        Types allowed in shapefile export
        """
        return [cls.Point, cls.LineString, cls.Polygon, cls.MultiPoint,
                cls.MultiLineString, cls.MultiPolygon]

    @classmethod
    def shape_allowed_type_names(cls):
        """
        Name types allowed in shapefile export
        """
        return [geom_type.label for geom_type in cls.shape_allowed_types()]
