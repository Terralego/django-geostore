import json

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, LineString, Point, GEOSException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..helpers import Routing


class RoutingViewsSetMixin:
    if 'geostore.routing' in settings.INSTALLED_APPS:
        @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
        def route(self, request, pk=None):
            layer = self.get_object()
            callback_id = self.request.data.get('callbackid', None)

            try:
                geometry = GEOSGeometry(str(request.data.get('geom')))
                if not isinstance(geometry, LineString):
                    raise ValueError

            except (GEOSException, TypeError, ValueError):
                return Response({"error": 'Provided geometry is not valid LineString'},
                                status=status.HTTP_400_BAD_REQUEST)

            points = [Point(c, srid=geometry.srid) for c in geometry.coords]
            routing = Routing(points, layer)
            route = routing.get_route()

            if not route:
                return Response(status=status.HTTP_204_NO_CONTENT)

            way = routing.get_linestring()
            response_data = {
                'request': {
                    'callbackid': callback_id,
                    'geom': json.loads(geometry.geojson),
                },
                'route': route,
                'geom': json.loads(way.geojson)
            }

            return Response(response_data)
