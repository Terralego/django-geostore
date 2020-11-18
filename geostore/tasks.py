from celery import shared_task
from django.apps import apps

from geostore.exports.helpers import generate_shapefile
from geostore.helpers import send_mail_export, save_generated_file, get_user_layer


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


@shared_task
def generate_async(function_generate, layer_id, user_id, format):
    layer, user = get_user_layer(layer_id, user_id)

    file = function_generate(layer)

    path = save_generated_file(user_id, layer.name, format, file) if file else None
    send_mail_export(user, path)


@shared_task
def generate_shapefile_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    file = generate_shapefile(layer)

    path = save_generated_file(user_id, layer.name, 'zip', file.getvalue()) if file else None
    send_mail_export(user, path)
