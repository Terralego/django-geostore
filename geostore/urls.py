from django.utils.module_loading import import_string

from geostore import settings as app_settings
from django.urls import path, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

# Layer ViewsSet can be override by settings
layer_viewsset = import_string(app_settings.GEOSTORE_LAYER_VIEWSSET)

router.register(r'layer', layer_viewsset)
router.register(r'group', views.LayerGroupViewsSet, basename='group'),
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', views.FeatureViewSet,
                basename='feature')

urlpatterns = [
    path('', include(router.urls)),
]
