from django.conf import settings
from django.contrib.gis.geos import LineString
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_gis import serializers as geo_serializers


class RoutingSerializer(serializers.Serializer):
    geom = geo_serializers.GeometryField(help_text=_("A linestring with ordered waypoints."))
    callback_id = serializers.CharField(required=False, help_text=_("Optional callback id to match with your request."))
    route = serializers.JSONField(read_only=True, help_text=_("All features used, in geojson format."))
    way = geo_serializers.GeometryField(read_only=True, help_text=_("Routed way, as Linestring."), precision=6)

    def validate_geom(self, value):
        if not isinstance(value, LineString):
            raise ValidationError(_("Geometry should be a LineString object."))
        if not value.srid:
            value.srid = settings.INTERNAL_GEOMETRY_SRID
        return value
