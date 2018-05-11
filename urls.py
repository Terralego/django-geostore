from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework_jwt import views as auth_views

from .views import LayerViewSet, FeatureViewSet, LayerRelationViewSet, \
                   FeatureRelationViewSet

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
    # schemas
    path('swagger/',
         schema_view.with_ui('swagger', cache_timeout=None),
         name='schema-swagger-ui'),
    path('redoc/',
         schema_view.with_ui('redoc', cache_timeout=None),
         name='schema-redoc'),
    path('', include('terracommon.trrequests.urls'))
]

router = routers.SimpleRouter()

router.register(r'layer', LayerViewSet)
router.register(r'layer/(?P<layer_pk>\d+)/feature', FeatureViewSet)
router.register(r'layer_relation', LayerRelationViewSet)
router.register(r'layer_relation/(?P<layerrelation_pk>\d+)/feature_relation',
                FeatureRelationViewSet)

urlpatterns += router.urls
