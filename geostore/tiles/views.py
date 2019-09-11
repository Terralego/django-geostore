from django.views.generic.detail import BaseDetailView

from ..models import Layer, LayerGroup
from .mixins import (MultipleTileJsonMixin, MultipleTileResponseMixin,
                     TileJsonMixin, TileResponseMixin)


class TileJsonView(TileJsonMixin, BaseDetailView):
    model = Layer


class MultipleTileJsonView(MultipleTileJsonMixin, BaseDetailView):
    model = LayerGroup


class LayerTileDetailView(TileResponseMixin, BaseDetailView):
    model = Layer


class LayerGroupTileDetailView(MultipleTileResponseMixin, BaseDetailView):
    model = LayerGroup
