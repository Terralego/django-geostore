from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from ..models import Layer
from .helpers import VectorTile


class MVTView(APIView):

    permission_classes = ()

    def get_tile(self):
        big_tile = b''

        for layer in self.layers:
            feature_count, tile = self.get_tile_for_layer(layer)
            if feature_count:
                big_tile += tile
        return big_tile

    def get_tile_for_layer(self, layer):
        tile = VectorTile(layer)
        features = layer.features.all()
        return tile.get_tile(self.x, self.y, self.z, features)

    @swagger_auto_schema(
        responses={
            200: 'Returns a protobuf mapbox vector tile',
            404: 'The layer group does not exist'
            }
    )
    def get(self, request, group, z, x, y):
        if not settings.MAX_TILE_ZOOM > z > settings.MIN_TILE_ZOOM:
            return HttpResponse(status=204)
        self.z = z
        self.x = x
        self.y = y

        self.layers = Layer.objects.filter(group=group)

        if self.layers.count() == 0:
            return HttpResponseNotFound()

        return HttpResponse(
                    self.get_tile(),
                    content_type="application/vnd.mapbox-vector-tile"
                    )
