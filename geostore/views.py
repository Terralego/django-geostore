import json

from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import (GEOSException, GEOSGeometry, LineString,
                                     Point)
from django.core.serializers import serialize
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from .filters import JSONFieldFilterBackend
from .mixins import MultipleFieldLookupMixin
from .models import FeatureRelation, Layer, LayerRelation
from .permissions import FeaturePermission, LayerPermission
from .routing.helpers import Routing
from .serializers import (FeatureRelationSerializer, FeatureSerializer,
                          LayerRelationSerializer, LayerSerializer)


class LayerViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    permission_classes = (LayerPermission, )
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer
    lookup_fields = ('pk', 'name')

    @action(methods=['get', 'post'],
            url_name='shapefile', detail=True, permission_classes=[])
    def shapefile(self, request, pk=None):
        layer = self.get_object()

        if request.method not in SAFE_METHODS:
            if request.user.has_perm('geostore.can_import_layers'):
                try:
                    shapefile = request.data['shapefile']
                    with transaction.atomic():
                        layer.features.all().delete()
                        layer.from_shapefile(shapefile)
                        response = Response(status=status.HTTP_200_OK)
                except (ValueError, MultiValueDictKeyError):
                    response = Response(status=status.HTTP_400_BAD_REQUEST)
            else:
                self.permission_denied(request, 'Operation not allowed')
        else:
            if request.user.has_perm('geostore.can_export_layers'):
                shape_file = layer.to_shapefile()

                if shape_file:
                    response = HttpResponse(content_type='application/zip')
                    response['Content-Disposition'] = (
                        'attachment; '
                        f'filename="{layer.name}.zip"')

                    response.write(shape_file.getvalue())
                else:
                    response = Response(status=status.HTTP_204_NO_CONTENT)
            else:
                self.permission_denied(request, 'Operation not allowed')
        return response

    @action(detail=True, methods=['get'], url_name='geojson', permission_classes=[])
    def to_geojson(self, request, pk=None):
        if request.user.has_perm('geostore.can_export_layers'):
            layer = self.get_object()
            return JsonResponse(layer.to_geojson())
        else:
            self.permission_denied(request, 'Operation not allowed')

    @action(detail=True, methods=['post'], permission_classes=[])
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
            return Response(status=status.HTTP_204_NO_CONTENT)

        response_data = {
            'request': {
                'callbackid': callbackid,
                'geom': geometry.json,
            },
            'geom': route,
        }

        return Response(response_data, content_type='application/json')

    @action(detail=True, methods=['post'], permission_classes=[])
    def intersects(self, request, *args, **kwargs):
        layer = self.get_object()
        callbackid = self.request.data.get('callbackid', None)

        try:
            geometry = GEOSGeometry(request.data.get('geom', None))
        except (GEOSException, GDALException, TypeError, ValueError):
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


class FeatureViewSet(viewsets.ModelViewSet):
    permission_classes = (FeaturePermission, )
    serializer_class = FeatureSerializer
    filter_backends = (JSONFieldFilterBackend, )
    filter_fields = ('properties', )
    lookup_field = 'identifier'

    def _get_layer(self):
        queryfilter = Q(name=self.kwargs.get('layer'))
        if self.kwargs.get('layer').isdigit():
            queryfilter |= Q(pk=self.kwargs.get('layer'))

        return get_object_or_404(Layer, queryfilter)

    def get_serializer_context(self):
        """
        Layer access in serializer (pk to insure schema generation)
        """
        context = super().get_serializer_context()
        layer = self._get_layer()
        context.update({'layer_pk': layer.pk})
        return context

    def get_queryset(self):
        layer = self._get_layer()
        return layer.features.all()

    def perform_create(self, serializer):
        layer = self._get_layer()
        serializer.save(layer_id=layer.pk)


class LayerRelationViewSet(viewsets.ModelViewSet):
    queryset = LayerRelation.objects.all()
    serializer_class = LayerRelationSerializer


class FeatureRelationViewSet(viewsets.ModelViewSet):
    queryset = FeatureRelation.objects.all()
    serializer_class = FeatureRelationSerializer
