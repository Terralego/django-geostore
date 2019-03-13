from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.utils import get_files_tests


class ImportShapefileTest(TestCase):
    def test_default_group_nogroup(self):
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-WGS84.zip'),
            '-i', 'ID_PG',
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)

        # Assert the identifier is not an UUID4
        self.assertTrue(len(str(layer.features.first().identifier)) < 32)

    def test_reprojection(self):
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-RFG93.zip'),
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)

        # assert data was reprojected
        bbox = layer.features.first().get_bounding_box()
        self.assertTrue(-180 <= bbox[0])
        self.assertTrue(-90 <= bbox[1])
        self.assertTrue(bbox[2] <= 180)
        self.assertTrue(bbox[3] <= 90)

    def test_default_group(self):
        # Fake json
        foo_bar_json = get_files_tests('foo_bar.json')

        # Import a shapefile
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-WGS84.zip'),
            '-i', 'ID_PG',
            verbosity=0)

        # Ensure old settings
        layer = Layer.objects.all()[0]
        self.assertNotEqual('new_name', layer.name)
        self.assertNotEqual('new_group', layer.group)
        self.assertNotEqual({'foo': 'bar'}, layer.schema)
        self.assertNotEqual({'foo': 'bar'}, layer.settings)

        # Change settings
        call_command(
            'layer_edit',
            '-pk', layer.pk,
            '-l', 'new_name',
            '-gr', 'new_group',
            '-ls', foo_bar_json
        )

        # Ensure new settings
        layer = Layer.objects.all()[0]
        self.assertEqual('new_name', layer.name)
        self.assertEqual('new_group', layer.group)
        self.assertEqual({'foo': 'bar'}, layer.settings)

    def test_schema_generated(self):
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-WGS84.zip'),
            '-gs',
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.get()

        # Assert schema properties are presents
        self.assertNotEqual(
            layer.schema.get('properties').keys() -
            ['ALTITUDE', 'ETIQUETTE', 'HAUTEUR', 'ID', 'ID_PG', 'NATURE', 'NOM',
             'ORIGIN_BAT', 'PUB_XDECAL', 'PUB_YDECAL', 'ROTATION', 'ROTATION_S',
             'XDECAL', 'XDECAL_SYM', 'YDECAL', 'YDECAL_SYM', 'Z_MAX', 'Z_MIN', ], True)
