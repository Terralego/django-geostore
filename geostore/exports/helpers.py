from django.core.serializers import serialize

import fiona
from fiona.crs import from_epsg
import glob
import json
import os
from tempfile import TemporaryDirectory

from geostore import settings as app_settings
from geostore import GeometryTypes
from geostore.helpers import get_serialized_properties, make_zipfile_bytesio
from geostore.renderers import KMLRenderer


def generate_kml(layer):
    from geostore.serializers import FeatureSerializer
    if not layer.features.count():
        return
    return KMLRenderer().render(FeatureSerializer(layer.features.all(), many=True).data)


def generate_geojson(layer):
    if not layer.features.count():
        return
    return serialize('geojson',
                     layer.features.all(),
                     fields=('properties',),
                     geometry_field='geom',
                     properties_field='properties')


def generate_shapefile(layer):
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
