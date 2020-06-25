from django.conf import settings
from django.db import transaction

from geostore.tasks import feature_update_relations_destinations, layer_relations_set_destinations


def execute_async_func(async_func, args=()):
    """ Celery worker can be out of transaction, and raise DoesNotExist """
    async_func.delay(*args) if not transaction.get_connection().in_atomic_block else transaction.on_commit(
        lambda: async_func.delay(*args))


def save_feature(sender, instance, **kwargs):
    if settings.GEOSTORE_RELATION_CELERY_ASYNC:
        execute_async_func(feature_update_relations_destinations, (instance.pk,))


def save_layer_relation(sender, instance, **kwargs):
    if settings.GEOSTORE_RELATION_CELERY_ASYNC:
        execute_async_func(layer_relations_set_destinations, (instance.pk,))
