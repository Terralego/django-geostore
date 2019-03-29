from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.factories import LayerFactory
from terracommon.terra.tests.utils import get_files_tests


class ImportGeojsonTest(TestCase):
    def test_default_group(self):
        output = StringIO()
        call_command(
            'import_geojson', get_files_tests('empty.json'),
            verbosity=1, stdout=output)

        # Retrieve the layer
        layer = Layer.objects.first()
        self.assertIn(f'The created layer pk is {layer.pk}', output.getvalue())
        self.assertEqual('__nogroup__', layer.group)

    def test_default_group_nogroup_rollback(self):
        output = StringIO()
        call_command(
            'import_geojson',
            f'--dry-run', get_files_tests('empty.json'),
            verbosity=1, stdout=output)
        self.assertIn("The created layer pk is", output.getvalue())
        # Retrieve the layer
        self.assertEqual(Layer.objects.count(), 0)

    def test_schema_generated(self):
        call_command(
            'import_geojson',
            get_files_tests('bati.geojson'),
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

    def test_import_geojson_layer_with_bad_settings(self):
        empty_geojson = get_files_tests('empty.json')
        bad_json = get_files_tests('bad.json')
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_geojson',
                empty_geojson,
                '-ls', bad_json,
                verbosity=0)
        self.assertEqual("Please provide a valid layer settings file", str(error.exception))

    def test_import_geojson_layer_with_pk_layer(self):
        layer = LayerFactory()
        self.assertEqual(len(layer.features.all()), 0)
        geojson_sample = get_files_tests('toulouse.geojson')
        call_command(
            'import_geojson',
            f'--layer-pk={layer.pk}',
            geojson_sample,
            verbosity=0
        )
        self.assertEqual(len(layer.features.all()), 838)

    def test_import_geojson_layer_with_wrong_pk_layer(self):
        geojson_sample = get_files_tests('toulouse.geojson')
        with self.assertRaises(CommandError) as error:
            call_command(
                'import_geojson',
                f'--layer-pk=999',
                '-gs', geojson_sample,
                verbosity=0
            )
        self.assertIn("Layer with pk 999 doesn't exist", str(error.exception))
