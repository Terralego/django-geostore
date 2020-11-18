from django.db.models.signals import post_save
from django.dispatch import receiver

from geostore import settings as app_settings
from geostore.helpers import execute_async_func
from geostore.models import Feature, LayerRelation
from geostore.tasks import feature_update_relations_destinations, layer_relations_set_destinations


@receiver(post_save, sender=Feature)
def save_feature(sender, instance, **kwargs):
    if app_settings.GEOSTORE_RELATION_CELERY_ASYNC:
        execute_async_func(feature_update_relations_destinations, (instance.pk,))


@receiver(post_save, sender=LayerRelation)
def save_layer_relation(sender, instance, **kwargs):
    if app_settings.GEOSTORE_RELATION_CELERY_ASYNC:
        execute_async_func(layer_relations_set_destinations, (instance.pk,))
