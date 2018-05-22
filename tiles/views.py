import datetime
import json

import mercantile
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.serializers import serialize
from django.db.models import F
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseNotFound)
from django.shortcuts import get_object_or_404
from django.views.generic import View
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Feature, Layer
from .funcs import ST_AsMvtGeom, ST_MakeEnvelope, ST_Transform


class MVTView(View):
    def get_tile(self):
        bounds = mercantile.bounds(self.x, self.y, self.z)
        xmin, ymin = mercantile.xy(bounds.west, bounds.south)
        xmax, ymax = mercantile.xy(bounds.east, bounds.north)

        layer_query = self.layer.features.for_date(self.date_filter).annotate(
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
                   ST_AsMVT(tilegeom, 'name', 4096, 'geometry') AS mvt
            FROM tilegeom
            ''',
            args + (self.layer.pk, )
        )

        return mvt_query[0]

    def get(self, request, layer_pk, z, x, y):
        self.z = z
        self.x = x
        self.y = y

        self.date_filter = self.request.GET.get('date', datetime.date.today())
        self.layer = get_object_or_404(Layer, pk=layer_pk)

        qs = self.get_tile()
        if qs.count > 0:
            return HttpResponse(
                        qs.mvt,
                        content_type="application/vnd.mapbox-vector-tile"
                        )
        else:
            return HttpResponseNotFound()


class IntersectView(APIView):
    def post(self, request, layer_pk):
        layer = get_object_or_404(Layer, pk=layer_pk)

        try:
            geometry = GEOSGeometry(request.POST.get('geom', None))
        except TypeError:
            return HttpResponseBadRequest(
                        content='Provided geometry is not valid')

        return Response(json.loads(
                    serialize('geojson',
                              layer.features.intersects(geometry),
                              fields=('properties',),
                              geometry_field='geom',
                              properties_field='properties'),
                    ))
