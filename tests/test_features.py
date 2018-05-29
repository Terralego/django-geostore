import json
from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .factories import FeatureFactory, LayerFactory, TerraUserFactory


class FeaturesTestCase(TestCase):
    def setUp(self):
        features_dates = [
            {'from_date': '12-01', 'to_date': '02-01'},
            {'from_date': '04-01', 'to_date': '05-01'},
            {'from_date': '01-01', 'to_date': '03-01'},
            {'from_date': '10-01', 'to_date': '12-31'},
            {'from_date': '01-20', 'to_date': '12-20'},
        ]
        self.layer = LayerFactory.create(add_features=features_dates)
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
            self.assertEqual(count, self.layer.features.for_date(day).count())

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
        layer = LayerFactory()
        reference_geometry = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [
                                    1.109619140625,
                                    44.036269809534616
                                ],
                                [
                                    1.7633056640625,
                                    43.12103377575541
                                ]
                            ]
                        }
                    }
                ]
            }

        layer.from_geojson(
            from_date='01-01',
            to_date='12-31',
            geojson_data=json.dumps(reference_geometry))

        """The layer below must intersect"""
        response = self.client.post(
            reverse('layer-intersects', args=[layer.pk, ]),
            {
                'geom': '''
                    {
                        "type": "LineString",
                        "coordinates": [
                        [
                            1.856689453125,
                            43.92163712834673
                        ],
                        [
                            1.109619140625,
                            43.4249985081581
                        ]
                        ]
                    }
                '''
            }
        )

        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            reference_geometry.get('features')[0],
            response.json().get('features')[0]
        )

        """The layer below must NOT intersect"""
        response = self.client.post(
            reverse('layer-intersects', args=[layer.pk, ]),
            {
                'geom': '''
                    {
                        "type": "Point",
                        "coordinates": [
                        1.9940185546874998,
                        44.55133484083592
                        ]
                    }
                '''
            }
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.json().get('features')))

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
