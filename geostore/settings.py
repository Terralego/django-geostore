from django.conf import settings

TERRA_TILES_HOSTNAMES = getattr(settings, 'TERRA_TILES_HOSTNAMES', [])

MAX_TILE_ZOOM = getattr(settings, 'MAX_TILE_ZOOM', 15)
MIN_TILE_ZOOM = getattr(settings, 'MIN_TILE_ZOOM', 10)

INTERNAL_GEOMETRY_SRID = getattr(settings, 'INTERNAL_GEOMETRY_SRID', 4326)
GEOSTORE_RELATION_CELERY_ASYNC = getattr(settings, 'GEOSTORE_RELATION_CELERY_ASYNC', False)

# LayerViewSet can be override by a subclass
GEOSTORE_LAYER_VIEWSSET = getattr(settings, 'GEOSTORE_LAYER_VIEWSSET', 'geostore.views.LayerViewSet')
# LayerSerializer can be override by a subclass
GEOSTORE_LAYER_SERIALIZER = getattr(settings, 'GEOSTORE_LAYER_SERIALIZER', 'geostore.serializers.LayerSerializer')

GEOSTORE_EXPORT_CELERY_ASYNC = getattr(settings, 'GEOSTORE_EXPORT_CELERY_ASYNC', False)
