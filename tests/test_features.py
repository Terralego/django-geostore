import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase
from django.urls import reverse

from terracommon.accounts.tests.factories import TerraUserFactory

from .factories import FeatureFactory, LayerFactory


class FeaturesTestCase(TestCase):
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

    def test_to_geojson(self):
        response = self.client.get(reverse('layer-geojson',
                                           args=[self.layer.pk]))
        self.assertEqual(200, response.status_code)

        response = response.json()
        self.assertEqual('FeatureCollection', response.get('type'))
        self.assertEqual(self.layer.features.all().count(),
                         len(response.get('features')))

    def test_features_intersections(self):
        layer = LayerFactory(group=self.group_name)
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.intersect_ref_geometry)))

        """The layer below must intersect"""
        response = self.client.post(
            reverse('layer-intersects', args=[layer.pk, ]),
            {
                'geom': json.dumps(self.intersect_geometry)
            }
        )

        self.assertEqual(200, response.status_code)
        response = response.json().get('results', {})
        self.assertEqual(
            1,
            len(response.get('features'))
        )
        self.assertDictEqual(
            self.intersect_ref_geometry,
            response.get('features')[0].get('geometry')
        )

        """The layer below must NOT intersect"""
        response = self.client.post(
            reverse('layer-intersects', args=[layer.name, ]),
            {
                'geom': json.dumps(self.fake_geometry)
            }
        )

        self.assertEqual(200, response.status_code)

        response = response.json().get('results', {})
        self.assertEqual(0, len(response.get('features')))

        """Tests that the intersects view throw an error if geometry is
           invalid
        """
        response = self.client.post(
            reverse('layer-intersects', args=[layer.pk, ]),
            {
                'geom': '''Invalid geometry'''
            }
        )
        self.assertEqual(400, response.status_code)

    def test_features_linestring_format(self):
        response = self.client.post(
            reverse('layer-intersects', args=[self.group_name, ]),
            {
                'geom': json.dumps(self.fake_linestring)
            }
        )

        self.assertEqual(400, response.status_code)

    def test_features_polygon_format(self):
        response = self.client.post(
            reverse('layer-intersects', args=[self.group_name, ]),
            {
                'geom': json.dumps(self.fake_polygon)
            }
        )

        self.assertEqual(400, response.status_code)
