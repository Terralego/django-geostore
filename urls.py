from django.conf import settings
from django.http import HttpResponseNotFound
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers
from rest_framework_jwt import views as auth_views

from .tiles.views import MVTView, TilejsonView
from .views import (FeatureRelationViewSet, FeatureViewSet,
                    LayerRelationViewSet, LayerViewSet)

app_name = 'terra'

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
    # auth
    path('auth/obtain-token/',
         auth_views.obtain_jwt_token,
         name='token-obtain'),
    path('auth/verify-token/',
         auth_views.verify_jwt_token,
         name='token-verify'),
    path('auth/refresh-token/',
         auth_views.refresh_jwt_token,
         name='token-refresh'),
    path(r'layer/<str:group>/tilejson',
         TilejsonView.as_view(),
         name='group-tilejson'),
    path(r'layer/<str:group>/tiles/<int:z>/<int:x>/<int:y>/',
         MVTView.as_view(),
         name='group-tiles'),
    # Fake pattern to be able to reverse this
    path(r'layer/<str:group>/tiles/{z}/{x}/{y}/',
         lambda request, group: HttpResponseNotFound(),
         name='group-tiles-pattern'),
]

router = routers.SimpleRouter()

router.register(r'layer', LayerViewSet)
router.register(r'layer/(?P<layer>[\d\w\-_]+)/feature', FeatureViewSet,
                base_name='feature')
router.register(r'layer_relation', LayerRelationViewSet)
router.register(r'layer_relation/(?P<layerrelation_pk>\d+)/feature_relation',
                FeatureRelationViewSet)

urlpatterns += router.urls

if settings.DEBUG or settings.SWAGGER_ENABLED:
    urlpatterns += [
        # schemas
        path('swagger/',
             schema_view.with_ui('swagger', cache_timeout=0),
             name='schema-swagger-ui'),
        path('redoc/',
             schema_view.with_ui('redoc', cache_timeout=0),
             name='schema-redoc'),
    ]
