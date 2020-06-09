from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

from geostore.models import LayerGroup
from geostore.tests.factories import LayerFactory
from geostore.tiles.helpers import VectorTile, get_cache_version


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }})
class FillTilesCacheTestCase(TestCase):

    def setUp(self):
        self.layer = LayerFactory(name="layerLine")
        self.group = LayerGroup.objects.create(name='mygroup', slug='mygroup')
        self.group.layers.add(self.layer)

        self.layer.from_geojson(
            geojson_data='''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {
                    "foo": "bar",
                    "baba": "fifi"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                    [
                        1.3700294494628906,
                        43.603640347220924
                    ],
                    [
                        1.2984466552734375,
                        43.57902295875415
                    ]
                    ]
                }
                }
            ]
            }
        ''')

    def test_update_topology_routing_fail(self):
        tile = VectorTile(self.layer)
        cache_version = get_cache_version(self.layer)

        x, y, z = 515, 373, 10

        with self.assertNumQueries(9):
            call_command('fill_tiles_cache', stdout=StringIO())

        tile.get_tile(x, y, z)

        with self.assertNumQueries(0):
            self.assertIsNotNone(
                cache.get(
                    tile.get_tile_cache_key(x, y, z),
                    version=cache_version,
                )
            )
