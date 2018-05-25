import json
from datetime import date

import mercantile
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.serializers import serialize
from django.db.models import F
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotFound)
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.views.generic import View
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Feature, Layer
from .funcs import ST_AsMvtGeom, ST_MakeEnvelope, ST_Transform


class MVTView(View):

    def get_tile(self):
        tile = b''

        for layer in self.layers:
            tile += self.get_tile_for_layer(layer)
        return tile

    def get_tile_for_layer(self, layer):
        bounds = mercantile.bounds(self.x, self.y, self.z)
        xmin, ymin = mercantile.xy(bounds.west, bounds.south)
        xmax, ymax = mercantile.xy(bounds.east, bounds.north)

        layer_query = layer.features.for_date(self.date_filter).annotate(
                bbox=ST_MakeEnvelope(xmin, ymin, xmax, ymax, 3857),
                geom3857=ST_Transform('geom', 3857)
            ).filter(
                bbox__intersects=F('geom3857')
            ).annotate(
                geometry=ST_AsMvtGeom(
                    F('geom3857'),
                    'bbox',
                    4096,
                    256,
                    True
                )
            )

        layer_raw_query, args = layer_query.query.sql_with_params()

        mvt_query = Feature.objects.raw(
            f'''
            WITH tilegeom as ({layer_raw_query})
            SELECT %s AS id, count(*) AS count,
                   ST_AsMVT(tilegeom, %s, 4096, 'geometry') AS mvt
            FROM tilegeom
            ''',
            args + (layer.pk, layer.name)
        )

        return mvt_query[0].mvt

    def get(self, request, group, z, x, y):
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
    def post(self, request, layer_pk):
        layer = get_object_or_404(Layer, pk=layer_pk)
        date_filter = (parse_date(self.request.GET.get('date', ''))
                       or date.today())

        features = layer.features.for_date(date_filter)

        try:
            geometry = GEOSGeometry(request.POST.get('geom', None))
        except TypeError:
            return HttpResponseBadRequest(
                        content='Provided geometry is not valid')

        return Response(json.loads(
                    serialize('geojson',
                              features.intersects(geometry),
                              fields=('properties',),
                              geometry_field='geom',
                              properties_field='properties'),
                    ))
