import json
from copy import deepcopy

from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.core.serializers import serialize
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response

from geostore import settings as app_settings
from geostore.renderers import KMLRenderer, GPXRenderer
from .mixins import MultipleFieldLookupMixin
from ..filters import JSONFieldFilterBackend, JSONFieldOrderingFilter, JSONSearchField
from ..helpers import execute_async_func
from ..tasks import generate_shapefile_async, generate_geojson_async, generate_kml_async
from ..models import Layer, LayerGroup
from ..permissions import FeaturePermission, LayerPermission, LayerImportExportPermission
from ..renderers import GeoJSONRenderer
from ..serializers import (FeatureExtraGeomSerializer, FeatureSerializer)
from ..serializers.geojson import FinalGeoJSONSerializer
from ..tiles.mixins import MVTViewMixin, MultipleMVTViewMixin


class LayerGroupViewsSet(MultipleMVTViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LayerGroup.objects.all()
    lookup_field = 'slug'


class LayerViewSet(MultipleFieldLookupMixin, MVTViewMixin, viewsets.ModelViewSet):
    permission_classes = (LayerPermission, )
    queryset = Layer.objects.all()
    serializer_class = import_string(app_settings.GEOSTORE_LAYER_SERIALIZER)
    lookup_fields = ('pk', 'name')

    def post_shapefile_sync(self, request, layer):
        try:
            shape_file = request.FILES['shapefile']
            with transaction.atomic():
                layer.features.all().delete()
                layer.from_shapefile(shape_file)
                response = Response(status=status.HTTP_200_OK)

        except (ValueError, MultiValueDictKeyError):
            response = Response(status=status.HTTP_400_BAD_REQUEST)
        return response

    def get_shapefile_sync(self, request, layer):
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

    @action(methods=['get', 'post'], detail=True, permission_classes=[IsAuthenticated,
                                                                      LayerImportExportPermission])
    def shapefile(self, request, *args, **kwargs):
        layer = self.get_object()
        if request.method == 'POST':
            return self.post_shapefile_sync(request, layer)
        else:
            return self.get_shapefile_sync(request, layer)

    if app_settings.GEOSTORE_EXPORT_CELERY_ASYNC:
        @action(methods=['get'],
                url_name='shapefile_async', detail=True, permission_classes=[IsAuthenticated,
                                                                             LayerImportExportPermission])
        def shapefile_async(self, request, *args, **kwargs):
            if request.user.email:
                layer = self.get_object()
                execute_async_func(generate_shapefile_async, (layer.id, request.user.id))
                return Response(status=status.HTTP_202_ACCEPTED)
            return Response({"error": _("Your user has no mail address.")}, status=status.HTTP_406_NOT_ACCEPTABLE)

        @action(methods=['get'], detail=True, permission_classes=[IsAuthenticated, LayerImportExportPermission])
        def geojson(self, request, *args, **kwargs):
            if request.user.email:
                layer = self.get_object()
                execute_async_func(generate_geojson_async, (layer.id, request.user.id))
                return Response(status=status.HTTP_202_ACCEPTED)
            return Response({"error": _("Your user has no mail address.")}, status=status.HTTP_406_NOT_ACCEPTABLE)

        @action(methods=['get'], detail=True, permission_classes=[IsAuthenticated, LayerImportExportPermission])
        def kml(self, request, *args, **kwargs):
            if request.user.email:
                layer = self.get_object()
                execute_async_func(generate_kml_async, (layer.id, request.user.id))
                return Response(status=status.HTTP_202_ACCEPTED)
            return Response({"error": _("Your user has no mail address.")},
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def intersects(self, request, *args, **kwargs):
        layer = self.get_object()
        callbackid = self.request.data.get('callbackid', None)

        try:
            geometry = GEOSGeometry(request.data.get('geom', None))
        except (GEOSException, GDALException, TypeError, ValueError):
            return HttpResponseBadRequest(
                content=_('Geometry is not valid'))

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
                return HttpResponseBadRequest(_('An error occured parsing '
                                              'GeoJSON, verify your data'))
        else:
            return HttpResponseBadRequest(_('Features are missing in GeoJSON'))

    @action(detail=True, methods=['get'])
    def property_values(self, request, pk):
        """
          Returns all distinct values of specified GET "property" params from
          database for the specified layers.

          Note: if some record has no value for this property, None is contained in the
          result list.
        """

        property_to_list = request.query_params.get('property')
        if not property_to_list:
            return Response({'error': _('Invalid "property" GET parameter')},
                            status=status.HTTP_400_BAD_REQUEST)

        layer = self.get_object()
        result = layer.get_property_values(property_to_list)

        return Response(result)


class FeatureViewSet(viewsets.ModelViewSet):
    permission_classes = (FeaturePermission, )
    serializer_class = FeatureSerializer
    serializer_class_extra_geom = FeatureExtraGeomSerializer
    renderer_classes = (JSONRenderer, GeoJSONRenderer, BrowsableAPIRenderer, KMLRenderer, GPXRenderer)
    filter_backends = (JSONFieldFilterBackend, JSONFieldOrderingFilter, JSONSearchField)
    filter_fields = ('properties', )
    ordering_fields = ('id', 'identifier', 'created_at', 'updated_at')
    lookup_field = 'identifier'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layer = None

    def transform_serializer_geojson(self, serializer_class):
        if self.kwargs.get('format', 'json') == 'geojson':
            # auto override in geojson case
            class FinalClass(FinalGeoJSONSerializer, serializer_class):
                class Meta(FinalGeoJSONSerializer.Meta, serializer_class.Meta):
                    pass
            return FinalClass
        return serializer_class

    def get_serializer_class(self):
        original_class = super().get_serializer_class()
        return self.transform_serializer_geojson(original_class)

    def get_layer(self):
        if not self.layer:
            filters = Q(name=self.kwargs.get('layer'))
            if self.kwargs.get('layer').isdigit():
                filters |= Q(pk=self.kwargs.get('layer'))

            self.layer = get_object_or_404(Layer, filters)
        return self.layer

    def get_serializer_context(self):
        """
        Layer access in serializer (pk to insure schema generation)
        """
        context = super().get_serializer_context()
        layer = self.get_layer()
        context.update({'layer_pk': layer.pk})
        return context

    def get_queryset(self):
        layer = self.get_layer()
        qs = layer.features.all()
        qs = qs.prefetch_related('layer__relations_as_origin')
        return qs

    def perform_create(self, serializer):
        layer = self.get_layer()
        serializer.save(layer_id=layer.pk)

    def update(self, request, *args, **kwargs):
        """ override to keep unfilled properties in partial update case """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        if partial:
            # if partial, we update properties
            properties = deepcopy(instance.properties)
            properties.update(data.get('properties', {}))
            data['properties'] = properties
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @action(detail=True, methods=['get', 'put', 'patch', 'delete'],
            url_path=r'extra_geometry/(?P<id_extra_feature>\d+)', url_name='detail-extra-geometry')
    def extra_geometry(self, request, id_extra_feature, *args, **kwargs):
        feature = self.get_object()
        extra_geometry = get_object_or_404(feature.extra_geometries.all(), pk=id_extra_feature)
        extra_layer = extra_geometry.layer_extra_geom
        if request.method == 'GET':
            return Response(self.serializer_class_extra_geom(extra_geometry).data)
        if not extra_layer.editable:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        if request.method == 'DELETE':
            extra_geometry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif request.method in ('PUT', 'PATCH'):
            serializer = self.serializer_class_extra_geom(data=request.data, instance=extra_geometry)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path=r'extra_layer/(?P<id_extra_layer>\d+)',
            url_name='create-extra-geometry')
    def extra_layer_geometry(self, request, id_extra_layer, *args, **kwargs):
        feature = self.get_object()
        layer = self.get_layer()
        extra_layer = get_object_or_404(layer.extra_geometries.all(), pk=id_extra_layer)
        if not extra_layer.editable:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        serializer = self.serializer_class_extra_geom(data=request.data)
        if serializer.is_valid():
            serializer.save(feature=feature, layer_extra_geom=extra_layer)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, url_path=r'relation/(?P<id_relation>[\d-]+)/features')
    def relation(self, request, *args, **kwargs):
        feature = self.get_object()
        layer_relation = get_object_or_404(feature.layer.relations_as_origin.all(),
                                           pk=kwargs.get('id_relation'))
        qs = feature.get_stored_relation_qs(layer_relation)
        # keep original viewset filtering
        qs = self.filter_queryset(qs)
        # keep original viewset pagination
        page = self.paginate_queryset(qs)
        if page is not None and self.request.GET.get('format', '') != 'geojson':
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        if self.request.GET.get('format', '') == 'geojson':
            self.kwargs['format'] = "geojson"
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
