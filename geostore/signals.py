from django.db import transaction

from geostore import settings as app_settings
from geostore.tasks import feature_update_relations_destinations, layer_relations_set_destinations


def save_feature(sender, instance, **kwargs):
    def execute():
        # update relations
        feature_update_relations_destinations.delay(instance.pk) \
            if app_settings.GEOSTORE_RELATION_CELERY_ASYNC else feature_update_relations_destinations(instance.pk)

    if not transaction.get_connection().in_atomic_block:
        execute()
    else:
        transaction.on_commit(lambda: execute())


def save_layer_relation(sender, instance, **kwargs):
    def execute():
        layer_relations_set_destinations.delay(instance.pk) \
            if app_settings.GEOSTORE_RELATION_CELERY_ASYNC else layer_relations_set_destinations(instance.pk)

    # update relations
    if kwargs.get('created', False):
        if not transaction.get_connection().in_atomic_block:
            execute()
        else:
            transaction.on_commit(lambda: execute())
