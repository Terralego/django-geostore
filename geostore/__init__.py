from django.db.models import IntegerChoices

default_app_config = 'geostore.apps.GeostoreConfig'


class GeometryTypes(IntegerChoices):
    Point = 0
    LineString = 1
    # LinearRing 2
    Polygon = 3
    MultiPoint = 4
    MultiLineString = 5
    MultiPolygon = 6
    GeometryCollection = 7

    @classmethod
    def shape_allowed_types(cls):
        """
        Types allowed in shapefile export
        """
        excluded = [cls.GeometryCollection]
        return [geom_type for geom_type in cls if geom_type not in excluded]

    @classmethod
    def shape_allowed_type_names(cls):
        """
        Name types allowed in shapefile export
        """
        return [str(geom_type).split('.')[-1] for geom_type in cls.shape_allowed_types()]
