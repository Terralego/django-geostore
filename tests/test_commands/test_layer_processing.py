import os

from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer


class LayerProcessingTestCase(TestCase):
    def test_layer_processing(self):
        empty_json = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'files',
                                  'empty.json')

        call_command(
            'import_geojson',
            f'-g{empty_json}',
            f'-s{empty_json}',
            verbosity=0)

        # Retrieve the layer
        layer = Layer.objects.all()[0]

        call_command(
            'layer_processing',
            f'--layer-pk-ins={layer.id}',
            f'--make-valid',
            verbosity=0)

        self.assertEqual(len(Layer.objects.all()), 2)

    def test_layer_processing_by_name(self):
        empty_json = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'files',
                                  'empty.json')
        geojson = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'files',
                               'toulouse.geojson')

        call_command(
            'import_geojson',
            f'-g{geojson}',
            f'-s{empty_json}',
            verbosity=0)

        # Retrieve the layer
        in_layer = Layer.objects.all()[0]

        out_layer = Layer.objects.create(name='out')

        call_command(
            'layer_processing',
            f'--layer-name-ins={in_layer.name}',
            f'--layer-name-out={out_layer.name}',
            f'--sql-centroid',
            verbosity=0)

        out_layer = Layer.objects.get(name='out')
        self.assertTrue(len(out_layer.features.all()) > 0)
