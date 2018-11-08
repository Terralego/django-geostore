import json

from django.contrib.gis.geos import (GEOSException, GEOSGeometry, LineString,
                                     Point)
from django.core.serializers import serialize
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status, viewsets
from rest_framework.decorators import detail_route
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from terracommon.accounts.permissions import (IsPostOrToken,
                                              TokenBasedPermission)
from terracommon.core.mixins import MultipleFieldLookupMixin

from .filters import JSONFieldFilterBackend
from .models import FeatureRelation, Layer, LayerRelation
from .routing.helpers import Routing
from .serializers import (FeatureRelationSerializer, FeatureSerializer,
                          LayerRelationSerializer, LayerSerializer)


class LayerViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer
    lookup_fields = ('pk', 'name')

    @detail_route(methods=['get', 'post'],
                  url_path='shapefile',
                  permission_classes=(IsPostOrToken, ))
    def shapefile(self, request, pk=None):
        layer = self.get_object()

        if request.method not in SAFE_METHODS:

            try:
                shapefile = request.data['shapefile']
                with transaction.atomic():
                    layer.features.all().delete()
                    layer.from_shapefile(shapefile)
                    response = Response(status=status.HTTP_200_OK)
            except (ValueError, MultiValueDictKeyError):
                response = Response(status=status.HTTP_400_BAD_REQUEST)

        else:
            shape_file = layer.to_shapefile()

            if shape_file:
                response = HttpResponse(content_type='application/zip')
                response['Content-Disposition'] = (
                    'attachment; '
                    f'filename="{layer.name}.zip"')

                response.write(shape_file.getvalue())
            else:
                response = Response(status=status.HTTP_204_NO_CONTENT)

        return response

    @detail_route(methods=['get'], url_path='geojson',
                  permission_classes=(TokenBasedPermission,))
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
        except (GEOSException, TypeError, ValueError):
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

    @detail_route(methods=['post'])
    def intersects(self, request, *args, **kwargs):
        layer = self.get_object()
        callbackid = self.request.data.get('callbackid', None)

        try:
            geometry = GEOSGeometry(request.data.get('geom', None))
        except (GEOSException, TypeError, ValueError):
            return HttpResponseBadRequest(
                content='Provided geometry is not valid')

        response = {
            'request': {
                'callbackid': callbackid,
                'geom': geometry.json,
            },
            'results': json.loads(serialize('geojson',
                                  layer.features.intersects(geometry),
                                  fields=('properties',),
                                  geometry_field='geom',
                                  properties_field='properties')),
        }

        return Response(response)

    def partial_update(self, request, *args, **kwargs):

        if not request.user.has_perm('terra.can_update_features_properties'):
            self.permission_denied(request, 'Operation not allowed')

        layer = self.get_object()

        if 'features' in request.data:
            try:
                features = layer.update_geometries(request.data['features'])
                return Response(
                            json.loads(serialize('geojson',
                                       features,
                                       fields=('properties',),
                                       geometry_field='geom',
                                       properties_field='properties'))
                        )
            except (ValueError, KeyError):
                return HttpResponseBadRequest('An error occured parsing '
                                              'GeoJSON, verify your data')
        else:
            return HttpResponseBadRequest('Features are missing in GeoJSON')

        return self.to_geojson(request)


class FeatureViewSet(viewsets.ModelViewSet):
    serializer_class = FeatureSerializer
    swagger_schema = None  # FIXME: Temporary disable schema generation
    filter_backends = (JSONFieldFilterBackend, )
    filter_fields = ('properties', )

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
