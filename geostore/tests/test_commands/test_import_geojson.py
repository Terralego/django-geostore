from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from geostore.models import Layer
from geostore.tests.factories import LayerFactory
from geostore.tests.utils import get_files_tests


class ImportGeojsonTest(TestCase):
    def test_default_group(self):
        output = StringIO()
        call_command(
            'import_geojson',
            get_files_tests('empty.json'),
            '--verbosity=1',
            stdout=output
        )

        # Retrieve the layer
        layer = Layer.objects.first()
        self.assertIn(f'The created layer pk is {layer.pk}', output.getvalue())
        self.assertEqual(layer.layer_groups.count(), 1)
        self.assertEqual(layer.layer_groups.first().name, 'default')

    def test_default_group_nogroup_rollback(self):
        output = StringIO()
        call_command(
            'import_geojson',
            get_files_tests('empty.json'),
            '--dry-run',
            '--verbosity=1', stdout=output)
        self.assertIn("The created layer pk is", output.getvalue())
        # Retrieve the layer
        self.assertEqual(Layer.objects.count(), 0)

    def test_schema_generated(self):
        call_command(
            'import_geojson',
            get_files_tests('bati.geojson'),
            '--generate-schema',
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.get()

        # Assert schema properties are presents
        self.assertNotEqual(
            layer.generated_schema.get('properties').keys() -
            ['ALTITUDE', 'ETIQUETTE', 'HAUTEUR', 'ID', 'ID_PG', 'NATURE', 'NOM',
             'ORIGIN_BAT', 'PUB_XDECAL', 'PUB_YDECAL', 'ROTATION', 'ROTATION_S',
             'XDECAL', 'XDECAL_SYM', 'YDECAL', 'YDECAL_SYM', 'Z_MAX', 'Z_MIN', ], True)

    def test_import_geojson_layer_with_bad_settings(self):
        bad_json = get_files_tests('bad.json')
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_geojson',
                get_files_tests('empty.json'),
                f'--layer-settings={bad_json}',
                verbosity=0)
        self.assertEqual("Please provide a valid layer settings file", str(error.exception))

    def test_import_geojson_layer_with_pk_layer(self):
        layer = LayerFactory()
        self.assertEqual(len(layer.features.all()), 0)
        call_command(
            'import_geojson',
            get_files_tests('toulouse.geojson'),
            layer_pk=layer.pk,
            verbosity=0
        )
        self.assertEqual(len(layer.features.all()), 838)

    def test_import_geojson_layer_with_wrong_pk_layer(self):
        geojson_sample = get_files_tests('toulouse.geojson')
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_geojson',
                geojson_sample,
                '--layer-pk=999',
                '--generate-schema',
                '--verbosity=0'
            )
        self.assertIn("Layer with pk 999 doesn't exist", str(error.exception))
