from celery import shared_task

from .helpers import Routing


@shared_task
def feature_update_routing(feature, tolerance):
    """Update all feature topologies"""
    layer = feature.layer
    if getattr(layer, 'routable', False):
        features = type(feature).objects.filter(geom__dwithin=(feature.geom, tolerance)).values_list('pk', flat=True)
        Routing.update_topology(layer, features)
    return True
