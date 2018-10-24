from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.management.commands import import_osm


class ImportgeojsonTest(TestCase):
    def test_import_osm(self):
        query = ("area[name='Toulouse']->.b;"
                 "(node['amenity'='bar'](area.b);way['amenity'='bar']"
                 "(area.b);relation['amenity'='bar'](area.b););out center;"
                 )
        type_feature = 'points'
        with mock.patch.object(import_osm, 'Command') as mocked:
            call_command(
                'import_osm',
                f'{query}',
                f'-t{type_feature}')
            self.assertEquals(mocked.call_count, 1)
