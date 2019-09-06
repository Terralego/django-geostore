from django.conf import settings

HOSTNAME = getattr(settings, 'HOSTNAME', '')
TERRA_TILES_HOSTNAMES = getattr(settings, 'TERRA_TILES_HOSTNAMES', [HOSTNAME, ])

SWAGGER_ENABLED = getattr(settings, 'SWAGGER_ENABLED', False)

MAX_TILE_ZOOM = getattr(settings, 'MAX_TILE_ZOOM', 15)
MIN_TILE_ZOOM = getattr(settings, 'MIN_TILE_ZOOM', 10)

INTERNAL_GEOMETRY_SRID = getattr(settings, 'INTERNAL_GEOMETRY_SRID', 4326)
