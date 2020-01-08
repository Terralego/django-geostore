from django.contrib.gis.geos import GEOSGeometry, LineString, Point, GEOSException
from django.http import HttpResponseBadRequest
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..helpers import Routing


class RoutingViewsSetMixin:
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
