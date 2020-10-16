from celery import shared_task

from .helpers import Routing


@shared_task
def feature_update_routing(feature, tolerance):
    """Update all feature topologies"""
    layer = feature.layer
    if layer.routable:
        features = layer.features.filter(geom__dwithin=(feature.geom, tolerance)).values_list('pk', flat=True)
        Routing.update_topology(layer, features)
    return True
