import json

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from terracommon.terra.tiles.helpers import VectorTile

from .factories import LayerFactory


@override_settings(DEBUG=True, CACHES={
    'default': {
        'BACKEND': ('django.core.cache.backends'
                    '.locmem.LocMemCache')
    }})
class VectorTilesTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        self.layer = LayerFactory(group=self.group_name)

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

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_tilejson(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.group_name]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(200, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = json.loads(response.content)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)

    def test_vector_tiles_view(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('group-tiles', args=[self.group_name, 13, 4126, 2991]))
        self.assertEqual(200, response.status_code)
        self.assertGreater(len(response.content), 0)
        query_count = len(connection.queries)
        original_content = response.content

        # verify data is cached
        response = self.client.get(
            reverse('group-tiles', args=[self.group_name, 13, 4126, 2991]))
        self.assertEqual(
            len(connection.queries),
            query_count - 2
        )
        self.assertEqual(
            original_content,
            response.content
        )

        response = self.client.get(
            reverse('group-tiles',
                    args=[self.group_name, 13, 1, 1]))

        self.assertEqual(200, response.status_code)
        self.assertEqual(b'', response.content)

    def test_caching_geometry(self):
        features = self.layer.features.all()
        tile = VectorTile(self.layer)
        x, y, z = 16506, 11966, 15
        pixel_buffer, features_filter, properties_filter, features_limit = \
            4, None, None, 10000

        cached_tile = tile.get_tile(
            x, y, z,
            pixel_buffer, features_filter, properties_filter, features_limit,
            features)
        self.assertEqual(cached_tile, cache.get(tile.get_tile_cache_key(
            x, y, z,
            pixel_buffer, features_filter, properties_filter, features_limit)))
        features[0].clean_vect_tile_cache()
        self.assertIsNone(cache.get(tile.get_tile_cache_key(
            x, y, z,
            pixel_buffer, features_filter, properties_filter, features_limit)))

    def test_caching_key(self):
        features = self.layer.features.all()
        tile = VectorTile(self.layer, "CACHINGCACHE")
        x, y, z = 16506, 11966, 15
        pixel_buffer, features_filter, properties_filter, features_limit = \
            4, None, None, 10000

        cached_tile = tile.get_tile(
            x, y, z,
            pixel_buffer, features_filter, properties_filter, features_limit,
            features)
        self.assertEqual(cached_tile, cache.get(tile.get_tile_cache_key(
            x, y, z,
            pixel_buffer, features_filter, properties_filter, features_limit)))

    def test_filtering(self):
        features = self.layer.features.all()
        tile = VectorTile(self.layer, "CACHINGCACHE")
        x, y, z = 16506, 11966, 15
        pixel_buffer, features_filter, properties_filter, features_limit = \
            4, {'baba': 'fifi2'}, ['foo'], 10000

        tile = tile.get_tile(
            x, y, z,
            pixel_buffer, features_filter, properties_filter, features_limit,
            features)
        self.assertGreater(len(tile), 0)
