from django.http import HttpResponseNotFound
from django.urls import path, include
from rest_framework import routers

from .tiles.views import (LayerGroupTileDetailView, LayerTileDetailView,
                          MultipleTileJsonView, TileJsonView)
from .views import (FeatureRelationViewSet, FeatureViewSet,
                    LayerRelationViewSet, LayerViewSet)


app_name = 'geostore'

router = routers.SimpleRouter()

router.register(r'layer', LayerViewSet)
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', FeatureViewSet,
                base_name='feature')
router.register(r'layer_relation', LayerRelationViewSet)
router.register(r'layer_relation/(?P<layerrelation_pk>\d+)/feature_relation',
                FeatureRelationViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('group/<str:slug>/tilejson',
         MultipleTileJsonView.as_view(),
         name='group-tilejson'),
    path('layer/<int:pk>/tilejson',
         TileJsonView.as_view(),
         name='layer-tilejson'),
    path('group/<str:slug>/tiles/<int:z>/<int:x>/<int:y>/',
         LayerGroupTileDetailView.as_view(),
         name='group-tiles'),
    # Fake pattern to be able to reverse this
    path('group/<str:slug>/tiles/{z}/{x}/{y}/',
         lambda request, **kwargs: HttpResponseNotFound(),
         name='group-tiles-pattern'),
    path('layer/<int:pk>/tiles/<int:z>/<int:x>/<int:y>/',
         LayerTileDetailView.as_view(),
         name='layer-tiles'),
    # Fake pattern to be able to reverse this
    path('layer/<int:pk>/tiles/{z}/{x}/{y}/',
         lambda request, **kwargs: HttpResponseNotFound(),
         name='layer-tiles-pattern'),
]
