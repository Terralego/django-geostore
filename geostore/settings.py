from django.conf import settings
from django.core.signals import setting_changed
from rest_framework.settings import APISettings as BaseAPISettings


DEFAULTS = {
    # Custom array to generate final absolute url for tilejson.
    # Default None : use request.build_absolute_url to handle correct full absolute url
    'TERRA_TILES_HOSTNAMES': None,
    # Max zoom value (Mapbox can auto scale max zoom +2)
    'MAX_TILE_ZOOM': 18,
    # Min zoom value (Mapbox can auto scale min zoom -2)
    'MIN_TILE_ZOOM': 2,
    # Used to define geometry internal SRID. Don't change after 1rst migration
    'INTERNAL_GEOMETRY_SRID': 4326,
    # Use a celery worker to launch sync relations (recommended if you use computed relations)
    'GEOSTORE_RELATION_CELERY_ASYNC': False
}


def get_old_user_settings():
    """ Backward compatibility with settings directly set in settings """
    return {
        key: getattr(settings, key, DEFAULTS[key]) for key in DEFAULTS
    }


USER_SETTINGS = getattr(settings, 'GEOSTORE', get_old_user_settings())


class APPSettings(BaseAPISettings):
    """ Redefinition to work in another app than rest_framework """
    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            # at first or after a reload (signal setting_changed)
            self._user_settings = getattr(settings, 'GEOSTORE', get_old_user_settings())
        return self._user_settings


app_settings = APPSettings(USER_SETTINGS, DEFAULTS, None)


def reload_api_settings(*args, **kwargs):
    setting = kwargs.get('setting')
    if setting in DEFAULTS.keys() or setting == 'GEOSTORE':
        app_settings.reload()


setting_changed.connect(reload_api_settings)
