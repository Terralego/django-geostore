from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from geostore.models import Layer
from geostore.tests.factories import LayerFactory
from geostore.tests.utils import get_files_tests


class ImportShapefileTest(TestCase):
    def test_default_group_nogroup(self):
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-WGS84.zip'),
            identifier='ID_PG',
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual(layer.layer_groups.count(), 1)
        self.assertEqual(layer.layer_groups.first().name, 'default')

        # Assert the identifier is not an UUID4
        self.assertTrue(len(str(layer.features.first().identifier)) < 32)

    def test_default_group_nogroup_rollback(self):
        # Sample ShapeFile
        shapefile_path = get_files_tests('shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')

        output = StringIO()
        call_command(
            'import_shapefile',
            sample_shapefile.name,
            identifier='ID_PG',
            dry_run=True,
            verbosity=1,
            stdout=output)
        self.assertIn("The created layer pk is", output.getvalue())
        # Retrieve the layer
        layer = Layer.objects.all()
        self.assertEqual(len(layer), 0)

    def test_reprojection(self):
        output = StringIO()
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-RFG93.zip'),
            verbosity=1, stdout=output)

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual(layer.layer_groups.count(), 1)
        self.assertEqual(layer.layer_groups.first().name, 'default')

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
            identifier='ID_PG',
            verbosity=0)

        # Ensure old settings
        layer = Layer.objects.all()[0]
        self.assertNotEqual('new_name', layer.name)
        self.assertEqual(layer.layer_groups.count(), 1)
        self.assertEqual(layer.layer_groups.first().name, 'default')
        self.assertNotEqual({'foo': 'bar'}, layer.generated_schema)
        self.assertNotEqual({'foo': 'bar'}, layer.settings)

        # Change settings
        call_command(
            'layer_edit',
            layer='new_name',
            layer_pk=layer.pk,
            groups=['new_group', ],
            layer_settings=open(foo_bar_json)
        )

        # Ensure new settings
        layer = Layer.objects.all()[0]
        self.assertEqual('new_name', layer.name)
        self.assertEqual(layer.layer_groups.count(), 1)
        self.assertEqual(layer.layer_groups.first().name, 'new_group')
        self.assertEqual({'foo': 'bar'}, layer.settings)

    def test_schema_generated(self):
        call_command(
            'import_shapefile',
            get_files_tests('shapefile-WGS84.zip'),
            generate_schema=True,
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.get()

        # Assert schema properties are presents
        self.assertNotEqual(
            layer.generated_schema.get('properties').keys() -
            ['ALTITUDE', 'ETIQUETTE', 'HAUTEUR', 'ID', 'ID_PG', 'NATURE', 'NOM',
             'ORIGIN_BAT', 'PUB_XDECAL', 'PUB_YDECAL', 'ROTATION', 'ROTATION_S',
             'XDECAL', 'XDECAL_SYM', 'YDECAL', 'YDECAL_SYM', 'Z_MAX', 'Z_MIN', ], True)

    def test_import_shapefile_layer_with_bad_settings(self):
        # Sample ShapeFile
        shapefile_path = get_files_tests('shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')
        bad_settings_json = get_files_tests('bad.json')
        # Change settings
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_shapefile',
                sample_shapefile.name,
                identifier='ID_PG',
                generate_schema=True,
                layer_settings=open(bad_settings_json),
                verbosity=0
            )
        self.assertEqual("Please provide a valid layer settings file", str(error.exception))

    def test_import_shapefile_layer_with_pk_layer(self):
        # Sample ShapeFile
        layer = LayerFactory()
        self.assertEqual(len(layer.features.all()), 0)
        shapefile_path = get_files_tests('shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')
        call_command(
            'import_shapefile',
            sample_shapefile.name,
            layer_pk=layer.pk,
            identifier='ID_PG',
            generate_schema=True,
            verbosity=0
        )
        self.assertEqual(len(layer.features.all()), 8)

    def test_import_shapefile_layer_with_wrong_pk_layer(self):
        # Sample ShapeFile
        shapefile_path = get_files_tests('shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_shapefile',
                sample_shapefile.name,
                layer_pk=999,
                identifier='ID_PG',
                generate_schema=True,
                verbosity=0
            )
        self.assertIn("Layer with pk 999 doesn't exist", str(error.exception))
