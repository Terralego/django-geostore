import json

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.status import (HTTP_200_OK, HTTP_204_NO_CONTENT,
                                   HTTP_404_NOT_FOUND)

from terracommon.terra.models import Layer
from terracommon.terra.tests.factories import LayerFactory
from terracommon.terra.tests.utils import get_files_tests
from terracommon.terra.tiles.helpers import (VectorTile, guess_maxzoom,
                                             guess_minzoom)


@override_settings(DEBUG=True, CACHES={
    'default': {
        'BACKEND': ('django.core.cache.backends'
                    '.locmem.LocMemCache')
    }})
class VectorTilesNoLayerTestCase(TestCase):
    group_name = 'mygroup'

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_tilejson_fail_no_layer(self):
        response = self.client.get(
            reverse('terra:group-tilejson', args=[self.group_name]),
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_404_NOT_FOUND, response.status_code)

    def test_vector_tiles_view_without_layer(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('terra:group-tiles', args=[self.group_name, 10, 515, 373]))
        self.assertEqual(HTTP_404_NOT_FOUND, response.status_code)
        self.assertEqual(len(response.content), 0)


@override_settings(DEBUG=True, CACHES={
    'default': {
        'BACKEND': ('django.core.cache.backends'
                    '.locmem.LocMemCache')
    }})
class VectorTilesTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        settings = {'metadata': {'attribution': 'plop'}}

        self.layer = LayerFactory(group=self.group_name, name="layerLine", settings=settings)

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

        self.layerPoint = LayerFactory(group="yourgroup", name="layerPoint", settings=settings)

        self.layerPoint.from_geojson(

            geojson_data='''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {
                    "foo": "bar"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        1.3700294494628906,
                        43.603640347220924
                    ]
                }
                }
            ]
            }
        ''')

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_tilejson(self):
        response = self.client.get(
            reverse('terra:group-tilejson', args=[self.group_name]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = json.loads(response.content)
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)

    def test_vector_tiles_view(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('terra:group-tiles', args=[self.group_name, 10, 515, 373]))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)
        query_count = len(connection.queries)
        original_content = response.content

        # verify data is cached
        response = self.client.get(
            reverse('terra:group-tiles', args=[self.group_name, 10, 515, 373]))
        self.assertEqual(
            len(connection.queries),
            query_count - 2
        )
        self.assertEqual(
            original_content,
            response.content
        )

        response = self.client.get(
            reverse('terra:group-tiles', args=[self.group_name, 10, 1, 1]))

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(b'', response.content)

    @override_settings(MAX_TILE_ZOOM=9)
    def test_vector_tiles_view_max_tile_zoom_lower_actual_zoom(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('terra:group-tiles', args=[self.group_name, 10, 515, 373]))
        self.assertEqual(HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(len(response.content), 0)

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

    def test_guess_maxzoom(self):

        # guess_maxzoom returning -1 when TypeError is raised14)
        self.assertEqual(
            guess_maxzoom(self.layerPoint),
            14)

        self.assertEqual(
            guess_maxzoom(self.layer) is not None,
            True)

        # test guess_maxzoom returns sensible value from OSM Fontainebleau paths&tracks
        chunk_fontainebleau_geojson = get_files_tests('chunk_fontainebleau.geojson')

        call_command(
            'import_geojson', chunk_fontainebleau_geojson,
            '-gr', 'maxzoom_test',
            '-ln', 'chunk_fontainebleau',
            verbosity=0)

        layer_chunk_fontainebleau = Layer.objects.get(name='chunk_fontainebleau')

        self.assertEqual(guess_maxzoom(layer_chunk_fontainebleau), 13)

    def test_guess_minzoom(self):

        self.assertEqual(
            guess_minzoom(self.layerPoint),
            0)

        self.assertTrue(isinstance(
            guess_minzoom(self.layer),
            int)
        )


class VectorTilesSpecialTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        # Same as default with properties filter not None
        settings = {'metadata': {'attribution': 'plop'}, 'tiles': {
            'minzoom': 0,
            'maxzoom': 22,
            'pixel_buffer': 4,
            'features_filter': None,  # Json
            'properties_filter': 'Test',  # Array of string
            'features_limit': 10000,
        }}

        self.layer = LayerFactory(group=self.group_name, name="layerLine", settings=settings)

        self.geojson_data = '''
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
        '''
        self.layer.from_geojson(geojson_data=self.geojson_data)

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_tilejson_with_properties(self):
        response = self.client.get(
            reverse('terra:group-tilejson', args=[self.group_name]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = json.loads(response.content)
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)
