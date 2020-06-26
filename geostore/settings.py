from django.conf import settings

# Define full http(s)://host alias to generate tilejson tiles full urls, to improve map performances
# Ex : ['http://a.tile.my.domain', 'http://b.tile.my.domain', 'http://c.tile.my.domain', ]
# Don't forget to redirect and allow these hosts in ALLOWED_HOST
TILE_HOSTNAMES = getattr(settings, 'GEOSTORE_TILE_HOSTNAMES', [])

# Define a default maximum zoom value for tile generation. Can be overrided in layer settings.
MAX_TILE_ZOOM = getattr(settings, 'GEOSTORE_MAX_TILE_ZOOM', 15)

# Define a default minimum zoom value for tile generation. Can be overrided in layer settings.
MIN_TILE_ZOOM = getattr(settings, 'GEOSTORE_MIN_TILE_ZOOM', 10)

# For the moment, 4326 only
INTERNAL_GEOMETRY_SRID = getattr(settings, 'GEOSTORE_INTERNAL_GEOMETRY_SRID', 4326)

# If you want use relations auto sync, add a celery worker and set to True
RELATION_CELERY_ASYNC = getattr(settings, 'GEOSTORE_RELATION_CELERY_ASYNC', False)


# Workaround to avoid breaking changes
if getattr(settings, 'TERRA_TILES_HOSTNAMES', None):
    TILE_HOSTNAMES = getattr(settings, 'TERRA_TILES_HOSTNAMES')

if getattr(settings, 'MAX_TILE_ZOOM', None) is not None:
    MAX_TILE_ZOOM = getattr(settings, 'MAX_TILE_ZOOM')

if getattr(settings, 'MIN_TILE_ZOOM', None) is not None:
    MIN_TILE_ZOOM = getattr(settings, 'MIN_TILE_ZOOM')

if getattr(settings, 'INTERNAL_GEOMETRY_SRID', None) is not None:
    INTERNAL_GEOMETRY_SRID = getattr(settings, 'INTERNAL_GEOMETRY_SRID')

# Last workaround if HOSTNAME is set and not TERRA_TILES_HOSTNAMES:
if getattr(settings, 'HOSTNAME', None) and not TILE_HOSTNAMES:
    TILE_HOSTNAMES = [getattr(settings, 'HOSTNAME'), ]
