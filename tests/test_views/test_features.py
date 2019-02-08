import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APIClient

from terracommon.accounts.tests.factories import TerraUserFactory
from terracommon.terra.models import Feature
from terracommon.terra.tests.factories import FeatureFactory, LayerFactory


class FeatureListPostTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = TerraUserFactory()

        self.client.force_authenticate(user=self.user)

        self.layer = LayerFactory(
            name="tree",
            schema={
                "name": {
                    "type": "string"
                },
                "age": {
                    "type": "integer"
                }
            })

    def test_feature_with_valid_properties_is_posted(self):
        """Feature with valid properties is successfully POSTed"""
        response = self.client.post(
                        reverse('terra:feature-list', args=[self.layer.id, ]),
                        {
                                "geom": "POINT(0 0)",
                                "layer": self.layer.id,
                                "name": "valid tree",
                                "age": 10,
                                "properties": {},
                        },
                        format='json',)
        features = Feature.objects.all()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].properties['name'], 'valid tree')

    def test_feature_with_missing_property_type_is_not_posted(self):
        """Feature with missing property type is not successfully POSTed"""
        response = self.client.post(
                        reverse('terra:feature-list', args=[self.layer.id, ]),
                        {
                            "geom": "POINT(0 0)",
                            "layer": self.layer.id,
                            "name": "invalid tree"
                        },
                        format='json')

        self.assertEqual(response.status_code, 400)


class FeaturesListGetTestCase(TestCase):
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

    group_name = 'mygroup'

    def setUp(self):
        self.layer = LayerFactory.create(group=self.group_name,
                                         add_features=5)

        self.user = TerraUserFactory()
        self.client.force_login(self.user)

    def test_features_filter_by_properties(self):
        layer = LayerFactory(group=self.group_name)
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
            reverse('terra:feature-list', kwargs={'layer_pk': layer.pk}),
            {'properties__number': 1, 'properties__text': 'foo'},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response['count'], 1)
        self.assertEqual(len(json_response['results']), 1)

    def test_features_filter_by_properties_with_wrong_field(self):
        layer = LayerFactory(group=self.group_name)
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
            reverse('terra:feature-list', kwargs={'layer_pk': layer.pk}),
            {'properties__wrongfield': 'wrong value'},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        json_response = response.json()
        self.assertEqual(json_response['count'], 0)
        self.assertEqual(len(json_response['results']), 0)

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
            reverse('terra:feature-list', kwargs={'layer_pk': layer.pk}),
            {'properties__number': 1, 'properties__digit': 42},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response['count'], 1)
        self.assertEqual(len(json_response['results']), 1)

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
            reverse('terra:feature-list', kwargs={'layer_pk': layer.pk}),
            {
                'properties__text': 'foobar',
                'properties__sentence': 'foobar is here'
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response['count'], 2)
        self.assertEqual(len(json_response['results']), 2)
