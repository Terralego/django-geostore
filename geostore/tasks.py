from celery import shared_task
from django.apps import apps

from geostore.import_export.exports import LayerExport
from geostore.import_export.helpers import get_user_layer, save_generated_file, send_mail_export


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
def generate_shapefile_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    layer_export = LayerExport(layer)
    file = layer_export.to_shapefile()

    path = save_generated_file(user_id, layer.name, 'zip', file.getvalue()) if file else None
    send_mail_export(user, path)


@shared_task
def generate_geojson_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    layer_export = LayerExport(layer)
    file = layer_export.to_geojson()

    path = save_generated_file(user_id, layer.name, 'zip', file) if file else None
    send_mail_export(user, path)


@shared_task
def generate_kml_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    layer_export = LayerExport(layer)
    file = layer_export.to_kml()
    path = save_generated_file(user_id, layer.name, 'zip', file) if file else None
    send_mail_export(user, path)
