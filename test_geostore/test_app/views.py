from rest_framework.decorators import action
from rest_framework.response import Response

from geostore.views import LayerViewSet


class ExtendedLayerViewsSet(LayerViewSet):
    @action(detail=False)
    def extended(self, request, *args, **kwargs):
        return Response({"extended": True})
