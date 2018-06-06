import json
from datetime import date

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .factories import FeatureFactory, LayerFactory, TerraUserFactory


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
    group_name = 'mygroup'

    def setUp(self):
        features_dates = [
            {'from_date': '12-01', 'to_date': '02-01'},
            {'from_date': '04-01', 'to_date': '05-01'},
            {'from_date': '01-01', 'to_date': '03-01'},
            {'from_date': '10-01', 'to_date': '12-31'},
            {'from_date': '01-20', 'to_date': '12-20'},
        ]
        self.layer = LayerFactory.create(group=self.group_name,
                                         add_features=features_dates)

        self.user = TerraUserFactory()
        self.client.force_login(self.user)

    def test_features_dates(self):
        dates = (
            (2, date(2018, 1, 5)),
            (3, date(2018, 1, 25)),
            (1, date(2019, 3, 15)),
            (2, date(2020, 4, 20)),
            (1, date(2007, 9, 1)),
            (3, date(2005, 12, 15)),
            (2, date(2021, 12, 25))
        )

        for count, day in dates:
            self.assertEqual(count,
                             self.layer.features.for_date(day, day).count())

    def test_feature_date_malformed(self):
        with self.assertRaises(ValidationError):
            FeatureFactory(from_date='1970-01-01', to_date='1970-01-01')

    def test_feature_date_illegal(self):
        with self.assertRaises(ValueError):
            FeatureFactory(from_date='99-99', to_date='99-99')

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
            from_date='01-01',
            to_date='12-31',
            geom=GEOSGeometry(json.dumps(self.intersect_ref_geometry)))

        """The layer below must intersect"""
        response = self.client.post(
            reverse('group-intersect', args=[self.group_name, ]),
            {
                'geom': json.dumps(self.intersect_geometry)
            }
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json().get('features')))
        self.assertDictEqual(
            self.intersect_ref_geometry,
            response.json().get('features')[0].get('geometry')
        )

        """The layer below must NOT intersect"""
        response = self.client.post(
            reverse('group-intersect', args=[self.group_name, ]),
            {
                'geom': json.dumps(self.fake_geometry)
            }
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.json().get('features')))

        """Tests that the intersects view throw an error if geometry is
           invalid
        """
        response = self.client.post(
            reverse('group-intersect', args=[self.group_name, ]),
            {
                'geom': '''Invalid geometry'''
            }
        )
        self.assertEqual(400, response.status_code)

    def test_features_dates_intersects(self):
        group_name = 'date_intersect'
        layer = LayerFactory(group=group_name)

        features = [
            {
                'from_date': '01-01',
                'to_date': '01-31',
                'properties': {
                    'number': 1,
                }
            }, {
                'from_date': '02-01',
                'to_date': '09-30',
                'properties': {
                    'number': 2,
                }
            }, {
                'from_date': '10-01',
                'to_date': '11-01',
                'properties': {
                    'number': 3,
                }
            }, {
                'from_date': '12-01',
                'to_date': '01-20',
                'properties': {
                    'number': 3,
                }
            }
        ]

        for feature in features:
            FeatureFactory(
                layer=layer,
                geom=json.dumps(self.intersect_ref_geometry),
                **feature
            )

        periods = (
            (date(2018, 1, 5), date(2018, 2, 5), 3, []),
            (date(2018, 4, 1), date(2018, 5, 1), 1, []),
            (date(2018, 8, 30), date(2018, 10, 10), 2, []),
            (date(2018, 11, 10), date(2018, 12, 10), 1, []),
        )

        for from_date, to_date, count, numbers in periods:
            response = self.client.post(
                reverse('group-intersect', args=[group_name, ]),
                {
                    'from': from_date,
                    'to': to_date,
                    'geom': json.dumps(self.intersect_geometry)
                }
            )
            self.assertEqual(count, len(response.json().get('features', None)))

    def test_features_sameidentifier_intersects(self):
        group_name = "sameidentifier"
        feature_identifier = "myidentifier"

        layer = LayerFactory(group=group_name)

        features = [
            {
                'from_date': '01-01',
                'to_date': '01-31',
                'properties': {
                    'number': 1,
                }
            }, {
                'from_date': '02-01',
                'to_date': '09-30',
                'properties': {
                    'number': 2,
                }
            }, {
                'from_date': '10-01',
                'to_date': '11-01',
                'properties': {
                    'number': 3,
                }
            }, {
                'from_date': '12-01',
                'to_date': '01-20',
                'properties': {
                    'number': 3,
                }
            }
        ]

        for feature in features:
            FeatureFactory(
                identifier=feature_identifier,
                layer=layer,
                geom=json.dumps(self.intersect_ref_geometry),
                **feature
            )

        response = self.client.post(
            reverse('group-intersect', args=[group_name, ]),
            {
                'from': date(2018, 8, 30),
                'to': date(2018, 10, 10),
                'geom': json.dumps(self.intersect_geometry)
            }
        )
        response = response.json()
        self.assertEqual(1, len(response.get('features')))
        self.assertEqual(2,
                         len(response.get('features')[0].get('properties')))
