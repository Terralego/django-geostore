from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from terracommon.terra.tiles.helpers import VectorTile

from .factories import LayerFactory


class VectorTilesTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        self.layer = LayerFactory(group=self.group_name)

        self.layer.from_geojson(
            from_date='01-01',
            to_date='12-31',
            geojson_data='''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {},
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

    def test_vector_tiles_view(self):
        response = self.client.get(
            reverse('group-tiles', args=[self.group_name, 13, 4126, 2991]))
        self.assertEqual(200, response.status_code)
        self.assertGreater(len(response.content), 0)

        response = self.client.get(reverse('group-tiles',
                                           args=[self.group_name, 1, 1, 1]))

        self.assertEqual(200, response.status_code)
        self.assertEqual(b'', response.content)

    def test_caching_geometry(self):
        features = self.layer.features.all()
        tile = VectorTile(self.layer)
        x, y, z = 16506, 11966, 15

        cached_tile = tile.get_tile(x, y, z, features)
        self.assertEqual(cached_tile,
                         cache.get(tile.get_tile_cache_key(x, y, z)))
        features[0].clean_vect_tile_cache()
        self.assertIsNone(cache.get(tile.get_tile_cache_key(x, y, z)))
