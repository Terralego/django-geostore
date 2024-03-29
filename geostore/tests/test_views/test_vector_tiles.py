import json
from unittest import skipIf
from urllib.parse import unquote, urljoin

from django.core.management import call_command
from django.db import connection
from django.contrib.gis.geos import LineString
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from rest_framework.test import APITestCase

from geostore import GeometryTypes
from geostore import settings as app_settings
from geostore.models import Layer, LayerGroup, LayerExtraGeom, LayerRelation, FeatureExtraGeom
from geostore.tests.factories import FeatureFactory, LayerFactory, LayerSchemaFactory
from geostore.tests.utils import get_files_tests
from geostore.tiles.helpers import VectorTile, guess_maxzoom, guess_minzoom


@override_settings(CACHES={
    'default': {
        'BACKEND': ('django.core.cache.backends'
                    '.locmem.LocMemCache')
    }})
class VectorTilesNoLayerTestCase(APITestCase):
    group_slug = 'mygroup'

    @override_settings(ALLOWED_HOSTS=['localhost'])
    def test_group_tilejson_fail_no_layer(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.group_slug]),
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_404_NOT_FOUND, response.status_code)

    def test_vector_tiles_view_without_layer(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('group-tiles', args=[self.group_slug, 10, 515, 373]))
        self.assertEqual(HTTP_404_NOT_FOUND, response.status_code)


@override_settings(DEBUG=True, CACHES={
    'default': {
        'BACKEND': ('django.core.cache.backends'
                    '.locmem.LocMemCache')
    }})
class VectorTilesTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        settings = {'metadata': {'attribution': 'plop'}}

        self.layer = LayerFactory(name="layerLine", settings=settings)
        self.layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                              geom_type=GeometryTypes.LineString,
                                                              title='Extra geometry')
        self.layer_relation = LayerSchemaFactory(name='layer_relation', geom_type=GeometryTypes.Polygon)
        self.feature_cover = FeatureFactory(layer=self.layer_relation, geom='POLYGON((0 0, 0 44, 3 44, 3 0, 0 0))')
        self.feature_not_cover = FeatureFactory(layer=self.layer_relation, geom='POLYGON((0 0, 0 43.579, 3 43.579, 3 0, 0 0))')

        self.mygroup = LayerGroup.objects.create(name='mygroup', slug='mygroup')
        self.mygroup.layers.add(self.layer)
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

        self.layerPoint = LayerFactory(name="layerPoint", settings=settings)
        self.yourgroup = LayerGroup.objects.create(name='yourgroup', slug='yourgroup')
        self.yourgroup.layers.add(self.layerPoint)
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

    def test_group_tilejson(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.mygroup.slug]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost'
        )
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tile_json = response.json()

        self.assertTrue(tile_json['attribution'])
        self.assertTrue(tile_json['description'] is None)
        self.assertGreater(len(tile_json['vector_layers']), 0)
        self.assertGreater(len(tile_json['vector_layers'][0]['fields']), 0)
        self.assertEqual(
            tile_json['tiles'][0],
            unquote(urljoin("http://localhost",
                            reverse('group-tiles-pattern',
                                    args=[self.mygroup.slug])))
        )

    def test_layer_tilejson(self):
        LayerRelation.objects.create(
            name="Polygon",
            relation_type='intersects',
            origin=self.layer,
            destination=self.layer_relation,
        )
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = response.json()
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)
        self.assertEqual(
            tilejson['tiles'][0],
            unquote(urljoin("http://localhost",
                            reverse('layer-tiles-pattern',
                                    args=[self.layer.pk])))
        )
        self.assertEqual(tilejson['vector_layers'], [{'description': 'Layerline',
                                                      'fields': {'baba': '', 'foo': ''},
                                                      'id': 'layerLine',
                                                      'maxzoom': 10,
                                                      'minzoom': 10},
                                                     {'description': 'Extra Geometry',
                                                      'fields': {},
                                                      'id': 'layerline-extra-geometry',
                                                      'maxzoom': 10,
                                                      'minzoom': 10},
                                                     {'description': 'Polygon',
                                                      'fields': {},
                                                      'id': 'relation-layerline-polygon',
                                                      'maxzoom': 22,
                                                      'minzoom': 0}])

    @skipIf(not app_settings.TERRA_TILES_HOSTNAMES, 'Test with custom tile hostnames only')
    def test_layer_tilejson_with_custom_hostnames(self):
        unquoted_reverse = unquote(reverse('layer-tiles-pattern', args=[self.layer.pk]))
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk])
        )
        self.assertEqual(HTTP_200_OK, response.status_code)
        tilejson = response.json()
        self.assertListEqual(
            tilejson['tiles'],
            [urljoin(host, unquoted_reverse) for host in app_settings.TERRA_TILES_HOSTNAMES]
        )

    def test_layer_tilejson_without_features(self):
        self.layer.features.all().delete()
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = response.json()
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)

    def test_404_tile_pattern(self):
        response = self.client.get(
            reverse(
                'layer-tiles-pattern',
                kwargs={'pk': self.layer.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vector_group_tiles_view(self):
        # first query that generate the cache
        response = self.client.get(
            reverse(
                'group-tiles',
                kwargs={'slug': self.mygroup.slug, 'z': 10, 'x': 515, 'y': 373}))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)
        query_count = len(connection.queries)
        original_content = response.content

        # verify data is cached
        response = self.client.get(
            reverse(
                'group-tiles',
                kwargs={'slug': self.mygroup.slug, 'z': 10, 'x': 515, 'y': 373}))
        self.assertEqual(
            len(connection.queries),
            query_count - 3
        )
        self.assertEqual(
            original_content,
            response.content
        )

        response = self.client.get(
            reverse('group-tiles', args=[self.group_name, 10, 1, 1]))

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertFalse(len(response.content))

    def test_vector_layer_tiles_view(self):
        # first query that generate the cache
        FeatureExtraGeom.objects.create(layer_extra_geom=self.layer_extra_geom,
                                        feature=self.layer.features.first(),
                                        geom=LineString((1.370029449462, 43.60364034724), (1.4, 43.61)))
        layer_relation = LayerRelation.objects.create(
            name="Polygon",
            relation_type='intersects',
            origin=self.layer,
            destination=self.layer_relation,
        )
        self.layer.features.first().sync_relations(layer_relation.pk)

        response = self.client.get(
            reverse(
                'layer-tiles',
                kwargs={'pk': self.layer.pk, 'z': 10, 'x': 515, 'y': 373}))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)
        self.assertIn(b'layerLine', response.content)
        self.assertIn(b'layerline-extra-geometry', response.content)
        self.assertIn(b'relation-layerline-polygon', response.content)
        query_count = len(connection.queries)
        original_content = response.content
        # verify data is cached
        response = self.client.get(
            reverse(
                'layer-tiles',
                kwargs={'pk': self.layer.pk, 'z': 10, 'x': 515, 'y': 373}))
        self.assertEqual(
            len(connection.queries),
            query_count - 5
        )
        self.assertEqual(
            original_content,
            response.content
        )

        response = self.client.get(
            reverse('layer-tiles', kwargs={'pk': self.layer.pk, 'z': 10, 'x': 1, 'y': 1}))

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(b'', response.content)

    @override_settings(MAX_TILE_ZOOM=9)
    def test_vector_group_tiles_view_max_tile_zoom_lower_actual_zoom(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('group-tiles', args=[self.mygroup.slug, 10, 515, 373]))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(len(response.content), 113)

    @override_settings(MAX_TILE_ZOOM=9)
    def test_vector_layer_tiles_view_max_tile_zoom_lower_actual_zoom(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('layer-tiles', args=[self.layer.pk, 10, 515, 373]))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(len(response.content), 113)

    def test_filtering(self):
        tile = VectorTile(self.layer, "CACHINGCACHE")
        x, y, z = 16506, 11966, 15

        tile = tile.get_tile(
            x, y, z
        )
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
            'properties_filter': ['Test', ],  # Array of string
            'features_limit': 10000,
        }}

        self.layer = LayerFactory(name="layerLine", settings=settings)
        self.group = LayerGroup.objects.create(name='mygroup', slug='mygroup')
        self.group.layers.add(self.layer)

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

    def test_group_tilejson_with_properties(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.group_name]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = response.json()
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)

    def test_layer_tilejson_with_properties(self):
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = json.loads(response.content)
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)
