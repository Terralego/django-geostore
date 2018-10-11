import os

from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer


class ImportshapefileTest(TestCase):
    def test_default_group(self):
        # Sample ShapeFile
        shapefile_path = os.path.join(
                    os.path.dirname(__file__),
                    'files',
                    'shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')

        # Fake json schema
        empty_geojson = os.path.join(os.path.dirname(__file__),
                                     'files',
                                     'empty.json')

        call_command(
            'import_shapefile',
            f'-iID_PG',
            f'-g{sample_shapefile.name}',
            f'-s{empty_geojson}')

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)

        # Assert the identifier is not an UUID4
        self.assertTrue(len(str(layer.features.first().identifier)) < 32)

    def test_reprojection(self):
        # Sample ShapeFile
        shapefile_path = os.path.join(
                    os.path.dirname(__file__),
                    'files',
                    'shapefile-RFG93.zip')
        sample_shapefile = open(shapefile_path, 'rb')

        # Create a fake json schema
        empty_geojson = os.path.join(os.path.dirname(__file__),
                                     'files',
                                     'empty.json')

        call_command(
            'import_shapefile',
            f'-g{sample_shapefile.name}',
            f'-s{empty_geojson}')

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)

        # assert data was reprojected
        bbox = layer.features.first().get_bounding_box()
        self.assertTrue(-180 <= bbox[0])
        self.assertTrue(-90 <= bbox[1])
        self.assertTrue(bbox[2] <= 180)
        self.assertTrue(bbox[3] <= 90)
