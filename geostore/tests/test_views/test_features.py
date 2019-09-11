import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK

from geostore.tests.factories import (FeatureFactory, LayerFactory)


class FeaturesListViewTest(TestCase):
    fake_geometry = {
        "type": "Point",
        "coordinates": [
            2.,
            45.
        ]
    }
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
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 1, 'text': 'bar'},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 1, 'text': 'foo'},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 2, 'text': 'foo'},
        )
        response = self.client.get(
            reverse('geostore:feature-list', kwargs={'layer': layer.pk}),
            {'properties__number': 1, 'properties__text': 'foo'},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(len(json_response), 1)

    def test_features_filter_by_properties_with_wrong_field(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 1},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 2},
        )
        response = self.client.get(
            reverse('geostore:feature-list', kwargs={'layer': layer.pk}),
            {'properties__wrongfield': 'wrong value'},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        json_response = response.json()
        self.assertEqual(len(json_response), 0)

    def test_features_filter_by_properties_with_several_int_field(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 2, 'digit': 42},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 1, 'digit': 42},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'number': 1, 'digit': 34},
        )
        response = self.client.get(
            reverse('geostore:feature-list', kwargs={'layer': layer.pk}),
            {'properties__number': 1, 'properties__digit': 42},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(len(json_response), 1)

    def test_features_filter_by_properties_with_several_string_field(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'text': 'foobar', 'sentence': 'foobar is here'},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'text': 'foo', 'sentence': 'foobar is missing'},
        )
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'text': 'foobar', 'sentence': 'foobar is here'},
        )
        response = self.client.get(
            reverse('geostore:feature-list', kwargs={'layer': layer.pk}),
            {
                'properties__text': 'foobar',
                'properties__sentence': 'foobar is here'
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(len(json_response), 2)

    def test_feature_from_layer_name(self):
        layer = LayerFactory()
        feature = FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.fake_geometry)),
            properties={'text': 'foobar', 'sentence': 'foobar is here'},
        )

        response = self.client.get(
            reverse(
                'geostore:feature-detail',
                kwargs={'layer': str(layer.name),
                        'identifier': str(feature.identifier)}
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
