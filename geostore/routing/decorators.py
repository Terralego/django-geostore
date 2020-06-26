from django.conf import settings

from geostore.routing.helpers import Routing


def topology_update(func):
    def wrapper(layer, *args, **kwargs):
        response = func(layer, *args, **kwargs)
        if 'geostore.routing' in settings.INSTALLED_APPS:
            Routing.create_topology(layer)
        return response

    return wrapper
