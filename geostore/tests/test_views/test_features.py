from unittest.mock import patch, PropertyMock

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.test import APITestCase

from geostore import GeometryTypes
from geostore.models import LayerRelation
from geostore.tests.factories import (FeatureFactory, LayerFactory, LayerSchemaFactory, UserFactory)


class FeaturesListViewTest(TestCase):
    fake_geometry = "POINT(2 45)"
    intersect_geometry = {
        "type": "LineString",
        "coordinates": [
            [
                1.3839340209960938,
                43.602521593464054
            ],
            [
                1.4869308471679688,
                43.60376465190968
            ]
        ]
    }
    intersect_ref_geometry = {
        "type": "LineString",
        "coordinates": [
            [
                1.440925598144531,
                43.64750394449096
            ],
            [
                1.440582275390625,
                43.574421623084234
            ]
        ]
    }
    fake_linestring = {
        "type": "LineString",
        "coordinates": [
            [
                1.3839340209960938,
                43.602521593464054
            ],
        ]
    }
    fake_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    1.3839340209960938,
                    43.602521593464054
                ],
                [
                    1.440582275390625,
                    43.574421623084234
                ]
            ]
        ]
    }

    def setUp(self):
        self.layer = LayerFactory.create(add_features=5)

    def test_features_filter_by_properties(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 1, 'text': 'bar'},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 1, 'text': 'foo'},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 2, 'text': 'foo'},
        )
        response = self.client.get(
            reverse('feature-list', kwargs={'layer': layer.pk}),
            {'properties__number': 1, 'properties__text': 'foo'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(len(json_response), 1)

    def test_features_filter_by_properties_with_wrong_field(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 1},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 2},
        )
        response = self.client.get(
            reverse('feature-list', kwargs={'layer': layer.pk}),
            {'properties__wrongfield': 'wrong value'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        json_response = response.json()
        self.assertEqual(len(json_response), 0)

    def test_features_filter_by_properties_with_several_int_field(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 2, 'digit': 42},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 1, 'digit': 42},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'number': 1, 'digit': 34},
        )
        response = self.client.get(
            reverse('feature-list', kwargs={'layer': layer.pk}),
            {'properties__number': 1, 'properties__digit': 42},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(len(json_response), 1)

    def test_features_filter_by_properties_with_several_string_field(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'text': 'foobar', 'sentence': 'foobar is here'},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'text': 'foo', 'sentence': 'foobar is missing'},
        )
        FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'text': 'foobar', 'sentence': 'foobar is here'},
        )
        response = self.client.get(
            reverse('feature-list', kwargs={'layer': layer.pk}),
            {
                'properties__text': 'foobar',
                'properties__sentence': 'foobar is here'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(len(json_response), 2)

    def test_feature_from_layer_name(self):
        layer = LayerFactory()
        feature = FeatureFactory(
            layer=layer,
            geom=self.fake_geometry,
            properties={'text': 'foobar', 'sentence': 'foobar is here'},
        )

        response = self.client.get(
            reverse(
                'feature-detail',
                kwargs={'layer': str(layer.name),
                        'identifier': str(feature.identifier)}
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_geojson_renderer(self):
        FeatureFactory.create_batch(
            50,
            layer=self.layer,
            geom=self.fake_geometry,
            properties={
                'test': 'name',
                'name': 'test'
            })
        response = self.client.get(
            reverse('feature-list', kwargs={'layer': self.layer.pk, 'format': 'geojson'})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertListEqual(sorted(list(('features', 'type'))), sorted(list(data.keys())))
        self.assertEqual(data['type'], "FeatureCollection")
        self.assertEqual(len(data['features']), self.layer.features.count())


@override_settings(GEOSTORE_RELATION_CELERY_ASYNC=True)
class FeatureDetailTestCase(APITestCase):
    def setUp(self) -> None:
        self.layer_trek = LayerSchemaFactory(geom_type=GeometryTypes.LineString)
        self.layer_city = LayerSchemaFactory(geom_type=GeometryTypes.Polygon)
        self.trek = FeatureFactory(layer=self.layer_trek, geom='LINESTRING(0 0, 1 1, 2 2, 3 3)')
        self.city_uncover = FeatureFactory(layer=self.layer_city,
                                           geom='POLYGON((4 4, 4 7, 7 7, 7 4, 4 4))',
                                           properties={
                                               "name": "Cahors",
                                               "age": 50000
                                           })
        self.detail_url = reverse('feature-detail', args=(self.layer_city.pk,
                                                          self.city_uncover.identifier,))
        self.super_user = UserFactory(is_superuser=True)
        self.client.force_authenticate(self.super_user)

    def test_feature_detail(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_patch_keep_properties(self):
        response = self.client.patch(self.detail_url, data={"properties": {"name": "Divona"}})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertListEqual(sorted(list(data['properties'].keys())),
                             sorted(['name', 'age']))

    def test_feature_put_replace_properties(self):
        response = self.client.put(self.detail_url, data={'geom': 'POLYGON((4 4, 4 7, 7 7, 7 4, 4 4))',
                                                          "properties": {"name": "Divona"}})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertListEqual(sorted(list(data['properties'].keys())),
                             sorted(['name', ]), data)

    def test_feature_put_point_empty_wkt(self):
        response = self.client.put(self.detail_url, data={'geom': 'POINT EMPTY',
                                                          "properties": {"name": "Divona"}})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertListEqual(sorted(list(data['properties'].keys())),
                             sorted(['name', ]), data)

    def test_feature_put_point_empty_geojson(self):
        response = self.client.put(self.detail_url, data={'geom': '{"type": "Point", "coordinates": []}',
                                                          "properties": {"name": "Divona"}})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data['geom'],
                         ['Unable to convert to python object: Invalid geometry pointer '
                          'returned from "OGR_G_CreateGeometryFromJson".'])

    @patch('geostore.settings.GEOSTORE_RELATION_CELERY_ASYNC', new_callable=PropertyMock)
    def test_relation(self, mock_relation):
        mock_relation.return_value = True
        city_cover = FeatureFactory(layer=self.layer_city, geom='POLYGON((0 0, 0 3, 3 3, 3 0, 0 0))')
        intersect_relation = LayerRelation.objects.create(
            relation_type='intersects',
            origin=self.layer_trek,
            destination=self.layer_city,
        )
        url = reverse('feature-relation', args=(self.layer_trek.pk,
                                                self.trek.identifier,
                                                intersect_relation.pk))
        # city cover should be present after sync
        self.trek.sync_relations(intersect_relation.pk)
        response = self.client.get(url, data={'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1, data)

        # city cover should not be present after deletion
        city_cover.delete()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 0, data)

    @patch('geostore.views.FeatureViewSet.pagination_class', new_callable=PropertyMock)
    def test_relation_with_pagination(self, mock_view):
        class MyPagination(PageNumberPagination):
            page_size = 1
            page_size_query_param = 'page_size'
        mock_view.return_value = MyPagination
        FeatureFactory(layer=self.layer_city, geom='POLYGON((0 0, 0 3, 3 3, 3 0, 0 0))')
        intersect_relation = LayerRelation.objects.create(
            relation_type='intersects',
            origin=self.layer_trek,
            destination=self.layer_city,
        )
        url = reverse('feature-relation', args=(self.layer_trek.pk,
                                                self.trek.identifier,
                                                intersect_relation.pk))
        # city cover should be present after sync
        self.trek.sync_relations(intersect_relation.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1, data)
        self.assertTrue(mock_view.called)
