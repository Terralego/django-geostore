from django.urls import path, include
from rest_framework import routers

from . import views

router = routers.SimpleRouter()

router.register(r'layer', views.LayerViewSet)
router.register(r'group', views.LayerGroupViewsSet, base_name='group'),
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', views.FeatureViewSet,
                base_name='feature')
router.register(r'layer_relation', views.LayerRelationViewSet)
router.register(r'layer_relation/(?P<layerrelation_pk>\d+)/feature_relation',
                views.FeatureRelationViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
