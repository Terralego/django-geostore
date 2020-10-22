from django.contrib.gis.db.models import (FloatField, GeometryField,
                                          IntegerField)
from django.db.models import Func


class RawGeometryField(GeometryField):
    def select_format(self, compiler, sql, params):
        """
        Override compiler format to not cast as bytea
        """
        return sql, params


class ST_AsMvtGeom(Func):
    function = 'ST_AsMvtGeom'
    output_field = RawGeometryField()


class ST_Transform(Func):
    function = 'ST_Transform'
    output_field = RawGeometryField()


class ST_MakeEnvelope(Func):
    function = 'ST_MakeEnvelope'
    output_field = RawGeometryField()


class ST_Distance(Func):
    function = 'ST_Distance'
    output_field = FloatField()


class ST_LineLocatePoint(Func):
    function = 'ST_LineLocatePoint'
    output_field = FloatField()


class ST_LineInterpolatePoint(Func):
    function = 'ST_LineInterpolatePoint'
    output_field = RawGeometryField()


class ST_Split(Func):
    function = 'ST_Split'
    output_field = RawGeometryField()


class ST_LineSubstring(Func):
    function = 'ST_LineSubstring'
    output_field = GeometryField()


class ST_SRID(Func):
    function = 'ST_SRID'
    output_field = IntegerField()


class ST_HausdorffDistance(Func):
    function = 'ST_HausdorffDistance'
    output_field = FloatField()


class ST_SnapToGrid(Func):
    function = 'ST_SnapToGrid'
    output_field = RawGeometryField()


class ST_Buffer(Func):
    function = 'ST_Buffer'
    output_field = RawGeometryField()


class ST_SetEffectiveArea(Func):
    function = 'ST_SetEffectiveArea'
    output_field = RawGeometryField()


class ST_Length(Func):
    function = 'ST_Length'
    output_field = FloatField()


class ST_Area(Func):
    function = 'ST_Area'
    output_field = FloatField()


class ST_MakeValid(Func):
    function = 'ST_MakeValid'
    output_field = RawGeometryField()


class ST_CollectionExtract(Func):
    function = 'ST_CollectionExtract'
    output_field = RawGeometryField()


class ST_SimplifyPreserveTopology(Func):
    function = 'ST_SimplifyPreserveTopology'
    output_field = RawGeometryField()
