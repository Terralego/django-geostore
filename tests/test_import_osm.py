from django.core.management import call_command
from django.test import TestCase

from terracommon.terra.models import Layer


class ImportgeojsonTest(TestCase):
    def test_get_nodes_osm(self):
        query_1 = "area[name='Toulouse']->.b;"
        query_2 = "(node['amenity'='bar'](area.b);way['amenity'='bar']"
        query_3 = "(area.b);relation['amenity'='bar'](area.b););out center;"
        query = ''.join((query_1, query_2, query_3))
        type_feature = 'points'
        call_command(
            'import_osm',
            f'{query}',
            f'-t{type_feature}')

        # Retrieve the layer
        layer = Layer.objects.all()[0]
        self.assertEqual('__nogroup__', layer.group)
