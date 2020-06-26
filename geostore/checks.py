from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def check_deprecated_settings(app_configs, **kwargs):
    errors = []
    if getattr(settings, 'HOSTNAME', None):
        errors.append(
            Warning(
                "HOSTNAME setting is deprecated for geostore. It will be removed in next version.",
                hint="Please set GEOSTORE_TILE_HOSTNAMES.",
                obj=None,
                id='geostore.W001',
            )
        )

    if getattr(settings, 'TERRA_TILES_HOSTNAMES', None):
        errors.append(
            Warning(
                "TERRA_TILES_HOSTNAMES setting is deprecated for geostore. It will be removed in next version.",
                hint="Please set GEOSTORE_TILE_HOSTNAMES.",
                obj=None,
                id='geostore.W002',
            )
        )

    if getattr(settings, 'MAX_TILE_ZOOM', None):
        errors.append(
            Warning(
                "MAX_TILE_ZOOM setting is deprecated for geostore. It will be removed in next version.",
                hint="Please set GEOSTORE_MAX_TILE_ZOOM.",
                obj=None,
                id='geostore.W003',
            )
        )

    if getattr(settings, 'MIN_TILE_ZOOM', None):
        errors.append(
            Warning(
                "MIN_TILE_ZOOM setting is deprecated for geostore. It will be removed in next version.",
                hint="Please fill GEOSTORE_MIN_TILE_ZOOM.",
                obj=None,
                id='geostore.W004',
            )
        )
    return errors


@register()
def check_backend_postgis(app_configs, **kwargs):
    errors = []

    if settings.DATABASES['default']['ENGINE'] != "django.contrib.gis.db.backends.postgis":
        errors.append(
            Error(
                "You should use postgis as default database engine.",
                hint="Use 'django.contrib.gis.db.backends.postgis'",
                obj=None,
                id='geostore.E001',
            )
        )
    return errors
