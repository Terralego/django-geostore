from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.utils import get_files_tests


class LayerEditTest(TestCase):
    def setUp(self):
        shapefile_path = get_files_tests('shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')
        call_command(
            'import_shapefile', sample_shapefile.name,
            '-i', 'ID_PG',
            verbosity=0)

    def test_layer_edit(self):
        # Ensure old settings
        layer = Layer.objects.all()[0]
        self.assertNotEqual('new_name', layer.name)
        self.assertNotEqual('new_group', layer.group)
        self.assertNotEqual({'foo': 'bar'}, layer.settings)

        foo_bar_json = get_files_tests('foo_bar.json')

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

    def test_layer_edit_fail_wrong_pk(self):
        # Ensure old settings

        foo_bar_json = get_files_tests('foo_bar.json')
        # Change settings
        with self.assertRaises(CommandError):
            call_command(
                'layer_edit',
                '-pk', 999,
                '-l', 'new_name',
                '-gr', 'new_group',
                '-s', foo_bar_json,
                '-ls', foo_bar_json
            )

    def test_layer_edit_with_bad_schema(self):
        layer = Layer.objects.first()
        bad_json = get_files_tests('bad.json')
        # Change settings
        with self.assertRaises(CommandError):
            call_command(
                'layer_edit',
                '-pk', layer.pk,
                '-l', 'new_name',
                '-gr', 'new_group',
                '-s', bad_json,
                '-ls', bad_json
            )

    def test_layer_edit_schema_bad_file(self):
        layer = Layer.objects.first()
        bad_file = get_files_tests('shapefile-RFG93.zip')
        # Change settings
        with self.assertRaises(CommandError):
            call_command(
                'layer_edit',
                '-pk', layer.pk,
                '-l', 'new_name',
                '-gr', 'new_group',
                '-s', bad_file,
                '-ls', bad_file
            )

    def test_layer_edit_bad_settings(self):
        layer = Layer.objects.first()
        bad_json = get_files_tests('bad.json')
        # Change settings
        with self.assertRaises(CommandError):
            call_command(
                'layer_edit',
                '-pk', layer.pk,
                '-l', 'new_name',
                '-gr', 'new_group',
                '-ls', bad_json
            )

    def test_layer_edit_guess_zoom(self):
        layer = Layer.objects.first()
        # Change settings
        call_command(
            'layer_edit',
            '-pk', layer.pk,
            '-l', 'new_name',
            '-gr', 'new_group',
            '-gz'
        )
        self.assertEqual(str(layer.settings), "{'tiles': {'maxzoom': 15, 'minzoom': 15}}")
