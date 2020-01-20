from celery import shared_task
from django.apps import apps


@shared_task
def feature_update_relations_destinations(feature_id, relation_id=None):
    """ Update all feature layer relations as origin """
    Feature = apps.get_model('geostore.Feature')
    feature = Feature.objects.get(pk=feature_id)
    feature.sync_relations(relation_id)

    return True


@shared_task
def layer_relations_set_destinations(relation_id):
    """ Update all feature layer as origin for a relation """
    LayerRelation = apps.get_model('geostore.LayerRelation')
    relation = LayerRelation.objects.get(pk=relation_id)

    for feature_id in relation.origin.features.values_list('pk', flat=True):
        feature_update_relations_destinations.delay(feature_id, relation_id)

    return True
