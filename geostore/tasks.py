from celery import shared_task
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.translation import ugettext as _

from geostore.exports.helpers import generate_geojson, generate_kml, generate_shapefile


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


def send_mail_generated_file(user, path):
    context = {"username": user.username, "file": path}
    html = get_template('geostore/emails/exports.html')
    html_content = html.render(context)
    txt = get_template('geostore/emails/exports.txt')
    txt_content = txt.render(context)
    send_mail(_('Your file is ready'), txt_content, None, [user.email], html_message=html_content, fail_silently=True)


def get_user_layer(layer_id, user_id):
    user = get_user_model().objects.get(id=user_id)
    Layer = apps.get_model('geostore.Layer')
    layer = Layer.objects.get(id=layer_id)
    return layer, user


@shared_task
def generate_shapefile_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)
    if not user.email:
        return
    file = generate_shapefile(layer)

    if file.getvalue():
        path = default_storage.save('exports/users/{}/{}.zip'.format(user.id, layer.name),
                                    ContentFile(file.getvalue()))
        send_mail_generated_file(user, path)


@shared_task
def generate_geojson_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)
    if not user.email:
        return
    json = generate_geojson(layer)

    if not json:
        return
    path = default_storage.save('exports/users/{}/{}.geojson'.format(user_id, layer.name),
                                ContentFile(json))
    send_mail_generated_file(user, path)


@shared_task
def generate_kml_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)
    if not user.email:
        return
    kml = generate_kml(layer)
    if not kml:
        return
    path = default_storage.save('exports/users/{}/{}.kml'.format(user_id, layer.name),
                                ContentFile(kml))
    send_mail_generated_file(user, path)
