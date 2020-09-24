import types

from django.conf import settings
from django.contrib.gis.geos import Point
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..helpers import Routing, RoutingException
from ..serializers import RoutingSerializer


class RoutingViewsSetMixin:
    if 'geostore.routing' in settings.INSTALLED_APPS:
        @action(detail=True, methods=['post'],
                serializer_class=RoutingSerializer,
                permission_classes=[IsAuthenticated])
        def route(self, request, pk=None):
            layer = self.get_object()
            data = request.data
            serializer = self.serializer_class(data=data)
            response_status = status.HTTP_200_OK

            if serializer.is_valid():
                geometry = serializer.validated_data['geom']

                try:
                    points = [Point(c, srid=geometry.srid) for c in geometry.coords]
                    routing = Routing(points, layer)
                    # route = routing.get_route()

                    # if not route:
                    #     return Response(status=status.HTTP_204_NO_CONTENT)

                    way = routing.get_linestring()

                    # generate response data by using serializer, to keep serialization rules (precision / perfs.)
                    response = types.SimpleNamespace()
                    response.geom = None
                    response.callback_id = None
                    response.route = None
                    response.way = way
                    serializer = self.serializer_class(response, data=request.data)
                    serializer.is_valid()
                    data = serializer.data
                    data['geom'] = request.data['geom']
                    data['callback_id'] = request.data.get('callback_id', None)

                except RoutingException as exc:
                    data = {"errors": [str(exc), ]}
                    response_status = status.HTTP_400_BAD_REQUEST

            else:
                data = serializer.errors
                response_status = status.HTTP_400_BAD_REQUEST

            return Response(data,
                            status=response_status)
