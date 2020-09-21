import json

from django.conf import settings
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..helpers import Routing
from ..serializers import RoutingSerializer


class RoutingViewsSetMixin:
    if 'geostore.routing' in settings.INSTALLED_APPS:
        @action(detail=True, methods=['post'],
                serializer_class=RoutingSerializer,
                permission_classes=[IsAuthenticated])
        def route(self, request, pk=None):
            layer = self.get_object()
            serializer = self.serializer_class(data=request.data)

            if serializer.is_valid():
                geometry = serializer.validated_data['geom']
                points = [Point(c, srid=geometry.srid) for c in geometry.coords]
                routing = Routing(points, layer)
                route = routing.get_route()

                if not route:
                    return Response(status=status.HTTP_204_NO_CONTENT)

                way = routing.get_linestring()
                response_data = {
                    'request': serializer.data,
                    'route': route,
                    'geom': json.loads(way.geojson)
                }
                return Response(response_data)

            else:
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)
