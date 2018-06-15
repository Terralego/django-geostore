import json
from datetime import date

from django.conf import settings
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.serializers import serialize
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotFound)
from django.utils.dateparse import parse_date
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Feature, Layer
from .helpers import VectorTile


class MVTView(APIView):

    permission_classes = ()

    def get_tile(self):
        big_tile = b''

        for layer in self.layers:
            feature_count, tile = self.get_tile_for_layer(layer)
            if feature_count:
                big_tile += tile
        return big_tile

    def get_tile_for_layer(self, layer):
        tile = VectorTile(layer)
        features = layer.features.for_date(self.date_from, self.date_to)
        return tile.get_tile(self.x, self.y, self.z, features)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'from', openapi.IN_QUERY, type=openapi.FORMAT_DATE),
            openapi.Parameter(
                'to', openapi.IN_QUERY, type=openapi.FORMAT_DATE),
            ],
        responses={
            200: 'Returns a protobuf mapbox vector tile',
            404: 'The layer group does not exist'
            }
    )
    def get(self, request, group, z, x, y):
        if not settings.MAX_TILE_ZOOM > z > settings.MIN_TILE_ZOOM:
            return HttpResponse(status=204)
        self.z = z
        self.x = x
        self.y = y

        self.layers = Layer.objects.filter(group=group)

        if self.layers.count() == 0:
            return HttpResponseNotFound()

        self.date_from = (parse_date(self.request.GET.get('from', ''))
                          or date.today())
        self.date_to = (parse_date(self.request.GET.get('to', ''))
                        or self.date_from)

        return HttpResponse(
                    self.get_tile(),
                    content_type="application/vnd.mapbox-vector-tile"
                    )


class IntersectView(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'callbackid', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                'from', openapi.IN_QUERY, type=openapi.FORMAT_DATE),
            openapi.Parameter(
                'to', openapi.IN_QUERY, type=openapi.FORMAT_DATE),
            openapi.Parameter(
                'geom', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            ],
        responses={
            200: 'serialized GeoJSON data',
            400: 'Geometry is incorrect'
            }
    )
    def post(self, request, group):
        date_from = (parse_date(self.request.POST.get('from', ''))
                     or date.today())
        date_to = (parse_date(self.request.POST.get('to', ''))
                   or date_from)
        callbackid = self.request.POST.get('callbackid', None)

        features = Feature.objects.filter(layer__group=group).for_date(
            date_from, date_to)

        try:
            geometry = GEOSGeometry(request.POST.get('geom', None))
        except (TypeError, ValueError):
            return HttpResponseBadRequest(
                        content='Provided geometry is not valid')

        results = {}
        for feature in features.intersects(geometry):
            feature.properties.update({
                'date_from': feature.from_date,
                'date_to': feature.to_date
            })

            if feature.identifier in results:
                (results[feature.identifier].properties
                    .append(feature.properties))
            else:
                feature.properties = [feature.properties, ]
                results[feature.identifier] = feature

        response = {
            'request': {
                'callbackid': callbackid,
                'geom': geometry.json,
            },
            'results': json.loads(serialize('geojson',
                                  results.values(),
                                  fields=('properties',),
                                  geometry_field='geom',
                                  properties_field='properties')),
        }

        return Response(response)
