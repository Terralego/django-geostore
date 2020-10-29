from celery import shared_task
from django.apps import apps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.utils.translation import ugettext as _

from geostore import settings as app_settings
from geostore.exports.helpers import generate_shapefile


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
def generate_shapefile_async(layer, user):
    file = generate_shapefile(layer)
    if file.getvalue() and user.email:
        path = default_storage.save('media/exports/users/{}/{}.zip'.format(user.id, layer.name),
                                    ContentFile(file.getvalue()))
        message = "{0} : {1}".format(_("Get your file"), path)
        send_mail(_('Your file is ready'), message, "coucou@coucou.coucou", [user.email], fail_silently=False)
