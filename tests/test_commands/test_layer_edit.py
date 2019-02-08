import os

from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer


class LayerEditTest(TestCase):
    def setUp(self):
        shapefile_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'files',
            'shapefile-WGS84.zip')
        sample_shapefile = open(shapefile_path, 'rb')

        empty_json = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'files',
                                  'empty.json')

        call_command(
            'import_shapefile',
            '-iID_PG',
            '-g', sample_shapefile.name,
            '-s', empty_json,
            verbosity=0)

    def test_layer_edit(self):
        # Ensure old settings
        layer = Layer.objects.all()[0]
        self.assertNotEqual('new_name', layer.name)
        self.assertNotEqual('new_group', layer.group)
        self.assertNotEqual({'foo': 'bar'}, layer.schema)
        self.assertNotEqual({'foo': 'bar'}, layer.settings)

        foo_bar_json = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    'files',
                                    'foo_bar.json')

        # Change settings
        call_command(
            'layer_edit',
            '-pk', layer.pk,
            '-l', 'new_name',
            '-gr', 'new_group',
            '-s', foo_bar_json,
            '-ls', foo_bar_json
        )

        # Ensure new settings
        layer = Layer.objects.all()[0]
        self.assertEqual('new_name', layer.name)
        self.assertEqual('new_group', layer.group)
        self.assertEqual({'foo': 'bar'}, layer.schema)
        self.assertEqual({'foo': 'bar'}, layer.settings)
