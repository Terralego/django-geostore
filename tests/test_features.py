import json
from datetime import date

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase
from django.urls import reverse

from .factories import LayerFactory, TerraUserFactory


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
            self.assertEqual(count, self.layer.features.for_date(day).count())

    def test_intersects(self):
        """Create a fake line geometry to intersect with"""
        self.layer.features.create(
            geom=GEOSGeometry(json.dumps(self.intersect_ref_geometry)),
            properties={},
            from_date='01-01',
            to_date='12-31'
        )

        response = self.client.post(
            reverse('group-intersect', args=[self.group_name]),
            {'geom': json.dumps(self.intersect_geometry), },
        )

        self.assertEqual(200, response.status_code)

        resp_data = response.json()

        self.assertEqual(1, len(resp_data.get('features')))
        self.assertDictEqual(self.intersect_ref_geometry,
                             resp_data.get('features')[0].get('geometry'))

        """Must not intersect with this point"""
        response = self.client.post(
            reverse('group-intersect', args=[self.group_name]),
            {'geom': json.dumps(self.fake_geometry), },)

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.json().get('features')))
