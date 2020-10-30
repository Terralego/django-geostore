from celery import shared_task
from django.apps import apps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _

from geostore.exports.helpers import generate_shapefile, generate_geojson


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
    html = get_template('email_async.html')
    html_content = html.render(context)
    send_mail(_('Your file is ready'), html_content, "coucou@coucou.coucou", [user.email], fail_silently=False)


@shared_task
def generate_shapefile_async(layer_id, user_id):
    User = apps.get_model('auth.User')
    user = User.objects.get(id=user_id)
    if not user.email:
        return

    Layer = apps.get_model('geostore.Layer')
    layer = Layer.objects.get(id=layer_id)
    file = generate_shapefile(layer)

    if file.getvalue():
        path = default_storage.save('exports/users/{}/{}.zip'.format(user.id, layer.name),
                                    ContentFile(file.getvalue()))
        send_mail_generated_file(user, path)


@shared_task
def generate_geojson_async(layer_id, user_id):
    User = apps.get_model('auth.User')
    user = User.objects.get(id=user_id)
    if not user.email:
        return

    Layer = apps.get_model('geostore.Layer')
    layer = Layer.objects.get(id=layer_id)
    json = generate_geojson(layer)

    if not json:
        return
    path = default_storage.save('exports/users/{}/{}.geojson'.format(user_id, layer.name),
                                ContentFile(json))
    send_mail_generated_file(user, path)
