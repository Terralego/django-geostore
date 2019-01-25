import os

from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer


class LayerProcessingTestCase(TestCase):
    def test_default_group(self):
        empty_geojson = os.path.join(os.path.dirname(__file__),
                                     'files',
                                     'empty.json')

        call_command(
            'import_geojson',
            f'-g{empty_geojson}',
            f'-s{empty_geojson}',
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.all()[0]

        call_command(
            'layer_processing',
            f'--layer-pk-ins={layer.id}',
            f'--make-valid',
            verbosity=0)

        self.assertEqual(len(Layer.objects.all()), 2)
