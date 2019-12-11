from geostore.routing.helpers import Routing


def topology_update(func):
    def wrapper(layer, *args, **kwargs):
        response = func(layer, *args, **kwargs)
        Routing.create_topology(layer)
        return response

    return wrapper
