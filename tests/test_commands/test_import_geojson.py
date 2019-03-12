from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.utils import get_files_tests


class ImportGeojsonTest(TestCase):
    def test_default_group(self):
        empty_geojson = get_files_tests('empty.json')

        call_command(
            'import_geojson', empty_geojson,
            verbosity=0)
        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)
