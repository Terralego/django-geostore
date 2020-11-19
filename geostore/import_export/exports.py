import glob
import json
import os
from tempfile import TemporaryDirectory

import fiona
from django.core.serializers import serialize
from fiona.crs import from_epsg

from geostore import GeometryTypes
from geostore import settings as app_settings
from geostore.import_export.helpers import make_zipfile_bytesio, get_serialized_properties
from geostore.renderers import KMLRenderer


class LayerExport:
    def __init__(self, layer):
        self.layer = layer

    def to_geojson(self):
        if not self.layer.features.count():
            return
        return serialize('geojson',
                         self.layer.features.all(),
                         fields=('properties',),
                         geometry_field='geom',
                         properties_field='properties')

    def to_shapefile(self):
        if not self.layer.features.count():
            return
        with TemporaryDirectory() as shape_folder:
            shapes = {}
            # get all accepted types if geom_type not defined, else keep selected
            type_to_check = GeometryTypes.shape_allowed_type_names() \
                if not self.layer.geom_type else \
                [self.layer.geom_type.name]

            # Create one shapefile by kind of geometry
            for geom_type in type_to_check:
                schema = {
                    'geometry': geom_type,
                    'properties': self.layer.layer_properties,
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
            for feature in self.layer.features.all():
                shapes[feature.geom.geom_type].write({
                    'geometry': json.loads(feature.geom.json),
                    'properties': get_serialized_properties(self.layer, feature.properties)
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

    def to_kml(self):
        from geostore.serializers import FeatureSerializer
        if not self.layer.features.count():
            return
        return KMLRenderer().render(FeatureSerializer(self.layer.features.all(), many=True).data)
