from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.factories import FeatureFactory, LayerFactory
from terracommon.terra.tests.utils import get_files_tests


def python_function(layers_in, layer_out, *args):
    layer_out.name = "New_name"
    layer_out.save()


def python_function_raise(*args):
    raise Exception


class LayerProcessingTestCase(TestCase):
    def test_layer_processing_make_valid(self):
        layer = LayerFactory()
        output = StringIO()

        call_command(
            'layer_processing',
            f'--layer-pk-ins={layer.id}',
            f'--make-valid',
            verbosity=1, stdout=output)
        self.assertIn('The created layer pk is', output.getvalue())
        self.assertEqual(len(Layer.objects.all()), 2)

    def test_layer_processing_make_valid_polygon(self):
        layer = LayerFactory()
        output = StringIO()

        call_command(
            'layer_processing',
            f'--layer-pk-ins={layer.id}',
            f'--make-valid',
            verbosity=1, stdout=output)
        self.assertIn('The created layer pk is', output.getvalue())
        self.assertEqual(len(Layer.objects.all()), 2)

    def test_layer_processing_make_valid_fail_multiple_pk_ins(self):
        layer_1 = LayerFactory()
        layer_2 = LayerFactory()
        with self.assertRaises(ValueError) as error:
            call_command(
                'layer_processing',
                f'--layer-name-ins={layer_1.name}',
                f'--layer-name-ins={layer_2.name}',
                f'--make-valid',
                verbosity=0)
        self.assertEqual(str(error.exception), 'Exactly one input layer required')

    def test_layer_processing_rollback(self):
        layer = LayerFactory()
        output = StringIO()

        call_command(
            'layer_processing',
            f'--layer-pk-ins={layer.id}',
            f'--make-valid',
            f'--dry-run',
            verbosity=1, stdout=output)
        self.assertIn('The created layer pk is', output.getvalue())
        self.assertEqual(len(Layer.objects.all()), 1)

    def test_layer_processing_by_name(self):
        geojson = get_files_tests('toulouse.geojson')

        call_command('import_geojson', geojson, verbosity=0)

        # Retrieve the layer
        in_layer = Layer.objects.first()

        out_layer = Layer.objects.create(name='out')
        FeatureFactory(layer=out_layer, properties="Test")

        call_command(
            'layer_processing',
            f'--layer-name-ins={in_layer.name}',
            f'--layer-name-out={out_layer.name}',
            f'--sql-centroid',
            verbosity=0)

        out_layer = Layer.objects.get(name='out')
        self.assertIn('Test', [feature.properties for feature in out_layer.features.all()])
        self.assertTrue(len(out_layer.features.all()) > 0)

    def test_layer_processing_by_pk(self):
        empty_json = get_files_tests('empty.json')
        geojson = get_files_tests('toulouse.geojson')

        call_command(
            'import_geojson',
            f'{geojson}',
            f'-ls={empty_json}',
            verbosity=0)

        # Retrieve the layer
        in_layer = Layer.objects.first()

        out_layer = LayerFactory(name='out')

        call_command(
            'layer_processing',
            f'--layer-name-ins={in_layer.name}',
            f'--layer-pk-out={out_layer.pk}',
            f'--sql-centroid',
            verbosity=0)

        out_layer = Layer.objects.get(name='out')
        self.assertTrue(out_layer.features.count() > 0)

    def test_layer_processing_fail_wrong_pk_in(self):
        with self.assertRaises(CommandError) as error:
            call_command(
                'layer_processing',
                f'--layer-pk-ins=999',
                f'--layer-name-out=out_fail',
                f'--sql-centroid',
                verbosity=0)
        self.assertIn("layer-pk-ins: 999", str(error.exception))

    def test_layer_processing_fail_wrong_name_in(self):
        with self.assertRaises(CommandError) as error:
            call_command(
                'layer_processing',
                f'--layer-name-ins=in_fail',
                f'--layer-name-out=out_fail',
                f'--sql-centroid',
                verbosity=0)
        self.assertIn("layer-name-ins: in_fail", str(error.exception))

    def test_layer_processing_fail_wrong_name_out(self):
        layer = LayerFactory()
        with self.assertRaises(CommandError) as error:
            call_command(
                'layer_processing',
                f'--layer-pk-ins={layer.pk}',
                f'--layer-name-out=out_fail',
                f'--sql-centroid',
                verbosity=0)
        self.assertIn("Layer with name out_fail doesn't exist", str(error.exception))

    def test_layer_processing_fail_wrong_pk_out(self):
        layer = LayerFactory()
        with self.assertRaises(CommandError) as error:
            call_command(
                'layer_processing',
                f'--layer-pk-ins={layer.pk}',
                f'--layer-pk-out=999',
                f'--sql-centroid',
                verbosity=0)
        self.assertIn("Layer with pk 999 doesn't exist", str(error.exception))

    def test_layer_processing_clear_output(self):
        geojson = get_files_tests('toulouse.geojson')

        call_command(
            'import_geojson',
            f'{geojson}',
            verbosity=0)

        # Retrieve the layer
        in_layer = Layer.objects.first()

        out_layer = LayerFactory(name='out')
        FeatureFactory(layer=out_layer, properties="Test")

        self.assertEqual(out_layer.features.count(), 1)
        call_command(
            'layer_processing',
            f'--layer-name-ins={in_layer.name}',
            f'--layer-pk-out={out_layer.pk}',
            f'--sql-centroid',
            f'-co',
            verbosity=0)

        out_layer = Layer.objects.get(name='out')
        self.assertTrue(out_layer.features.count() > 1)
        self.assertNotIn('Test', [feature.properties for feature in out_layer.features.all()])

    def test_layer_processing_python(self):
        layer = LayerFactory()
        call_command(
            'layer_processing',
            f'--layer-name-ins={layer.name}',
            f'--python=terracommon.terra.tests.test_commands.test_layer_processing.python_function',
            verbosity=0)
        self.assertTrue(Layer.objects.filter(name="New_name").exists())

    def test_layer_processing_python_raise(self):
        layer = LayerFactory()
        with self.assertRaises(Exception):
            call_command(
                'layer_processing',
                f'--layer-name-ins={layer.name}',
                f'--python=terracommon.terra.tests.test_commands.test_layer_processing.python_function_raise',
                verbosity=0)

    def test_layer_processing_sql_like_simple_sql(self):
        layer = LayerFactory()
        call_command(
            'layer_processing',
            f'--layer-name-ins={layer.name}',
            f'--sql=SELECT identifier, properties, ST_MakeValid(geom::geometry) AS geom FROM in0',
            verbosity=0)
        self.assertEqual(len(Layer.objects.all()), 2)
