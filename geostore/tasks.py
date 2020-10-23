from celery import shared_task
from django.apps import apps

import fiona
from fiona.crs import from_epsg
import glob
import json
import os
from tempfile import TemporaryDirectory

from . import settings as app_settings
from . import GeometryTypes
from .helpers import get_serialized_properties, make_zipfile_bytesio


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
def generate_shapefile(layer_id):
    Layer = apps.get_model('geostore.Layer')
    layer = Layer.objects.get(id=layer_id)
    if not layer.features.count():
        return
    with TemporaryDirectory() as shape_folder:
        shapes = {}
        # get all accepted types if geom_type not defined, else keep selected
        type_to_check = GeometryTypes.shape_allowed_type_names() \
            if not layer.geom_type else \
            [layer.geom_type.name]

        # Create one shapefile by kind of geometry
        for geom_type in type_to_check:
            schema = {
                'geometry': geom_type,
                'properties': layer.layer_properties,
            }

            shapes[geom_type] = fiona.open(
                shape_folder,
                layer=geom_type,
                mode='w',
                driver='ESRI Shapefile',
                schema=schema,
                encoding='UTF-8',
                crs=from_epsg(app_settings.INTERNAL_GEOMETRY_SRID)
            )

        # Export features to each kind of geometry
        for feature in layer.features.all():
            shapes[feature.geom.geom_type].write({
                'geometry': json.loads(feature.geom.json),
                'properties': get_serialized_properties(layer, feature.properties)
            })

        # Close fiona files
        for geom_type, shape in shapes.items():
            shape_size = len(shape)
            shape.close()

            # Delete empty shapes
            if not shape_size:
                for filename in glob.iglob(os.path.join(shape_folder, f'{geom_type}.*')):
                    os.remove(filename)

        # Zip to BytesIO and return shape files
        return make_zipfile_bytesio(shape_folder)
