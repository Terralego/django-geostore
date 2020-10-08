from celery import shared_task

from .helpers import Routing


@shared_task
def feature_update_routing(feature=None):
    """Update all feature topologies"""
    layer = feature.layer
    if getattr(layer, 'routable', False):
        Routing.create_topology(layer)
    return True