from django.urls import path, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'layer', views.LayerViewSet)
router.register(r'group', views.LayerGroupViewsSet, basename='group'),
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', views.FeatureViewSet,
                basename='feature')

urlpatterns = [
    path('', include(router.urls)),
]
