from django.contrib.gis.db.models import (IntegerField, FloatField,
                                          GeometryField)
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
