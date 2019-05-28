from enum import IntEnum


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
