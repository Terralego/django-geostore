from django.contrib.gis.geos import GEOSGeometry, LineString, Point
from django.http import HttpResponseBadRequest
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from .models import FeatureRelation, Layer, LayerRelation
from .serializers import (FeatureRelationSerializer, FeatureSerializer,
                          LayerRelationSerializer, LayerSerializer)
from .tiles.helpers import Routing


class LayerViewSet(viewsets.ModelViewSet):
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer

    @detail_route(methods=['get'], url_path='geojson')
    def to_geojson(self, request, pk=None):
        layer = self.get_object()
        return Response(layer.to_geojson())

    @detail_route(methods=['post'])
    def route(self, request, pk=None):
        layer = self.get_object()
        callbackid = self.request.data.get('callbackid', None)

        try:
            geometry = GEOSGeometry(request.data.get('geom', None))
            if not isinstance(geometry, LineString):
                raise ValueError
            points = [Point(c, srid=geometry.srid) for c in geometry.coords]
        except (TypeError, ValueError):
            return HttpResponseBadRequest(
                    content='Provided geometry is not valid LineString')

        routing = Routing(points, layer)
        route = routing.get_route()

        if not route:
            return Response(status=HTTP_204_NO_CONTENT)

        response_data = {
            'request': {
                'callbackid': callbackid,
                'geom': geometry.json,
            },
            'geom': route,
        }

        return Response(response_data, content_type='application/json')


class FeatureViewSet(viewsets.ModelViewSet):
    serializer_class = FeatureSerializer
    swagger_schema = None  # FIXME: Temporary disable schema generation

    def get_queryset(self):
        self.layer = get_object_or_404(Layer, pk=self.kwargs.get('layer_pk'))
        return self.layer.features.all()


class LayerRelationViewSet(viewsets.ModelViewSet):
    queryset = LayerRelation.objects.all()
    serializer_class = LayerRelationSerializer


class FeatureRelationViewSet(viewsets.ModelViewSet):
    queryset = FeatureRelation.objects.all()
    serializer_class = FeatureRelationSerializer
    swagger_schema = None  # FIXME: Temporary disable schema generation
