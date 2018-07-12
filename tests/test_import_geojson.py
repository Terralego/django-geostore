import json
import os
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer


class ImportgeojsonTest(TestCase):
    def test_default_group(self):
        # Create a fake geojson file
        tmp_geojson = NamedTemporaryFile(mode='w',
                                         suffix='.geojson',
                                         delete=False)
        json.dump({}, tmp_geojson)
        tmp_geojson.close()

        # Create a fake json schema
        tmp_schema = NamedTemporaryFile(mode='w',
                                        suffix='.json',
                                        delete=False)
        json.dump({}, tmp_schema)
        tmp_schema.close()

        call_command(
            'import_geojson',
            f'-g{tmp_geojson.name}',
            '-f 01-12', '-t 20-12',
            f'-s{tmp_schema.name}')

        os.remove(tmp_geojson.name)
        os.remove(tmp_schema.name)

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)
