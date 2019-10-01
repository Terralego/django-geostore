from enum import IntEnum

default_app_config = 'geostore.apps.GeostoreConfig'


class GeometryTypes(IntEnum):
    Point = 0
    LineString = 1
    # LinearRing 2
    Polygon = 3
    MultiPoint = 4
    MultiLineString = 5
    MultiPolygon = 6
    GeometryCollection = 7

    @classmethod
    def choices(cls):
        return [(geom_type.value, geom_type) for geom_type in cls]

    @classmethod
    def shape_allowed_types(cls):
        """
        Types allowed in shapefile export
        """
        excluded = [GeometryTypes.GeometryCollection]
        return [geom_type for geom_type in cls if geom_type not in excluded]

    @classmethod
    def shape_allowed_type_names(cls):
        """
        Name types allowed in shapefile export
        """
        return [geom_type.name for geom_type in cls.shape_allowed_types()]
