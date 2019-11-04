from django.urls import path, include
from rest_framework import routers

from .views import (FeatureRelationViewSet, FeatureViewSet,
                    LayerRelationViewSet, LayerViewSet, LayerGroupViewsSet)


app_name = 'geostore'

router = routers.SimpleRouter()

router.register(r'layer', LayerViewSet)
router.register(r'group', LayerGroupViewsSet, base_name='group'),
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', FeatureViewSet,
                base_name='feature')
router.register(r'layer_relation', LayerRelationViewSet)
router.register(r'layer_relation/(?P<layerrelation_pk>\d+)/feature_relation',
                FeatureRelationViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
