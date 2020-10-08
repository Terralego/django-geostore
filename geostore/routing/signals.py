from geostore import settings as app_settings
from geostore.signals import execute_async_func
from geostore.routing.tasks import feature_update_routing


def feature_routing(sender, instance, **kwargs):
    if instance.layer.routable:
        if app_settings.GEOSTORE_ROUTING_CELERY_ASYNC:
            execute_async_func(feature_update_routing, (instance.pk,))
        else:
            feature_update_routing(instance)

