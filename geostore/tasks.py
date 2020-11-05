from celery import shared_task
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.timezone import now
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


def send_mail_async(user, path=None):
    context = {"username": user.username, "file": path}
    if not path:
        template_email = 'exports_no_datas'
    else:
        template_email = 'exports'
    html = get_template('geostore/emails/{}.html'.format(template_email))
    html_content = html.render(context)
    txt = get_template('geostore/emails/{}.txt'.format(template_email))
    txt_content = txt.render(context)
    send_mail(_('Export ready'), txt_content, None, [user.email], html_message=html_content, fail_silently=True)


def save_generated_file(user_id, layer_name, format_file, string_file):
    path = default_storage.save('exports/users/{}/{}_{}.{}'.format(user_id,
                                                                   layer_name,
                                                                   int(now().timestamp()),
                                                                   format_file),
                                ContentFile(string_file))
    return path


def get_user_layer(layer_id, user_id):
    user = get_user_model().objects.get(id=user_id)
    Layer = apps.get_model('geostore.Layer')
    layer = Layer.objects.get(id=layer_id)
    return layer, user


@shared_task
def generate_shapefile_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    file = generate_shapefile(layer)

    if file:
        path = save_generated_file(user_id, layer.name, 'zip', file.getvalue())
        send_mail_async(user, path)
    else:
        send_mail_async(user)


@shared_task
def generate_geojson_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    json = generate_geojson(layer)

    if not json:
        send_mail_async(user)
    else:
        path = save_generated_file(user_id, layer.name, 'geojson', json)
        send_mail_async(user, path)


@shared_task
def generate_kml_async(layer_id, user_id):
    layer, user = get_user_layer(layer_id, user_id)

    kml = generate_kml(layer)

    if not kml:
        send_mail_async(user)
    else:
        path = save_generated_file(user_id, layer.name, 'kml', kml)
        send_mail_async(user, path)
