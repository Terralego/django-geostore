from .settings import *  # NOQA

TERRA_TILES_HOSTNAMES = [
    'http://a.tiles.local',
    'http://b.tiles.local',
    'http://c.tiles.local',
]

GEOSTORE_LAYER_VIEWSSET = 'test_geostore.test_app.views.ExtendedLayerViewsSet'
GEOSTORE_LAYER_SERIALIZER = 'test_geostore.test_app.serializers.ExtendedLayerSerializer'
GEOSTORE_EXPORT_CELERY_ASYNC = True
CELERY_ALWAYS_EAGER = True
