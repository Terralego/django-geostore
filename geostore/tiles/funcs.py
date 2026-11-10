from django.contrib.gis.db.models import FloatField
from django.contrib.gis.db.models.functions import GeoFunc, GeomOutputGeoFunc


class HausdorffDistance(GeoFunc):
    geom_param_pos = (0, 1)
    output_field = FloatField()


class SimplifyPreserveTopology(GeomOutputGeoFunc):
    pass


class Area(GeoFunc):
    output_field = FloatField()
