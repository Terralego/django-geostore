from django.conf import settings
from django.http import HttpResponseNotFound
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from .tiles.views import (LayerGroupTileDetailView, LayerTileDetailView,
                          MultipleTileJsonView, TileJsonView)
from .views import (FeatureRelationViewSet, FeatureViewSet,
                    LayerRelationViewSet, LayerViewSet)
from . import settings as app_settings

app_name = 'geostore'

schema_view = get_schema_view(
    openapi.Info(
        title="Terra PI",
        default_version='v1',
        description="The future of Makina Corpus",
    ),
    public=True,
    permission_classes=(permissions.AllowAny, ),
)

urlpatterns = [
    path(r'group/<str:slug>/tilejson',
         MultipleTileJsonView.as_view(),
         name='group-tilejson'),
    path(r'layer/<int:pk>/tilejson',
         TileJsonView.as_view(),
         name='layer-tilejson'),
    path(r'group/<str:slug>/tiles/<int:z>/<int:x>/<int:y>/',
         LayerGroupTileDetailView.as_view(),
         name='group-tiles'),
    # Fake pattern to be able to reverse this
    path(r'group/<str:slug>/tiles/{z}/{x}/{y}/',
         lambda request, **kwargs: HttpResponseNotFound(),
         name='group-tiles-pattern'),
    path(r'layer/<int:pk>/tiles/<int:z>/<int:x>/<int:y>/',
         LayerTileDetailView.as_view(),
         name='layer-tiles'),
    # Fake pattern to be able to reverse this
    path(r'layer/<int:pk>/tiles/{z}/{x}/{y}/',
         lambda request, **kwargs: HttpResponseNotFound(),
         name='layer-tiles-pattern'),
]

router = routers.SimpleRouter()

router.register(r'layer', LayerViewSet)
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', FeatureViewSet,
                base_name='feature')
router.register(r'layer_relation', LayerRelationViewSet)
router.register(r'layer_relation/(?P<layerrelation_pk>\d+)/feature_relation',
                FeatureRelationViewSet)

urlpatterns += router.urls

if settings.DEBUG or app_settings.SWAGGER_ENABLED:
    urlpatterns += [
        # schemas
        path('swagger/',
             schema_view.with_ui('swagger', cache_timeout=0),
             name='schema-swagger-ui'),
        path('redoc/',
             schema_view.with_ui('redoc', cache_timeout=0),
             name='schema-redoc'),
    ]
