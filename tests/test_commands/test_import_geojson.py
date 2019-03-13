from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.utils import get_files_tests


class ImportGeojsonTest(TestCase):
    def test_default_group(self):
        call_command(
            'import_geojson', get_files_tests('empty.json'),
            verbosity=0)
        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)

    def test_schema_generated(self):
        call_command(
            'import_shapefile',
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
