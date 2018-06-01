import json
from datetime import date

from django.conf import settings
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.serializers import serialize
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotFound)
from django.utils.dateparse import parse_date
from django.views.generic import View
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Feature, Layer
from .helpers import VectorTile


class MVTView(View):

    def get_tile(self):
        big_tile = b''

        for layer in self.layers:
            feature_count, tile = self.get_tile_for_layer(layer)
            if feature_count:
                big_tile += tile
        return tile

    def get_tile_for_layer(self, layer):
        tile = VectorTile(layer)
        features = layer.features.for_date(self.date_filter)
        return tile.get_tile(self.x, self.y, self.z, features)

    def get(self, request, group, z, x, y):
        if z > settings.MAX_TILE_ZOOM:
            return HttpResponseBadRequest()
        self.z = z
        self.x = x
        self.y = y

        self.layers = Layer.objects.filter(group=group)

        if self.layers.count() == 0:
            return HttpResponseNotFound()

        self.date_filter = (parse_date(self.request.GET.get('date', ''))
                            or date.today())

        return HttpResponse(
                    self.get_tile(),
                    content_type="application/vnd.mapbox-vector-tile"
                    )


class IntersectView(APIView):
    def post(self, request, group):
        date_filter = (parse_date(self.request.GET.get('date', ''))
                       or date.today())

        features = Feature.objects.for_date(
                    date_filter).filter(layer__group=group)

        try:
            geometry = GEOSGeometry(request.POST.get('geom', None))
        except (TypeError, ValueError):
            return HttpResponseBadRequest(
                        content='Provided geometry is not valid')

        return Response(json.loads(
                    serialize('geojson',
                              features.intersects(geometry),
                              fields=('properties',),
                              geometry_field='geom',
                              properties_field='properties'),
                    ))
