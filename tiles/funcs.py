from django.contrib.gis.db.models import GeometryField
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
