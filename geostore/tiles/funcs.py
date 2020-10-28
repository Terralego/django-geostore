from django.contrib.gis.db.models import FloatField, GeometryField
from django.contrib.gis.db.models.functions import GeoFunc
from django.db.models import Func


class MakeEnvelope(Func):
    function = "ST_MAKEENVELOPE"
    output_field = GeometryField()


class HausdorffDistance(GeoFunc):
    geom_param_pos = (0, 1)
    output_field = FloatField()


class SimplifyPreserveTopology(GeoFunc):
    pass


class Area(GeoFunc):
    output_field = FloatField()
