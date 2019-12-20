from geostore import settings as app_settings

from geostore.tasks import feature_update_relations_destinations


def save_feature(sender, instance, **kwargs):
    # update relations
    feature_update_relations_destinations.delay(instance.pk)\
        if app_settings.GEOSTORE_RELATION_CELERY_ASYNC else feature_update_relations_destinations(instance.pk)
