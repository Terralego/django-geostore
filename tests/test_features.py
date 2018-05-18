import json
from datetime import date

from django.urls import reverse
from django.test import TestCase

from django.contrib.gis.geos.geometry import GEOSGeometry

from terracommon.terra.models import Layer, Feature, TerraUser


class FeaturesTestCase(TestCase):
    fake_geometry = GEOSGeometry('''{
        "type": "Point",
        "coordinates": [
          2.4609375,
          45.583289756006316
        ]
      }''')
    def setUp(self):
        self.user = TerraUser.objects.create_user(
            email='foo@bar.com',
            password='123456'
        )
        self.layer = Layer.objects.create()

    def test_features_dates(self):
        self.layer.features.create(
            geom = self.fake_geometry,
            properties = {},
            from_date='12-01',
            to_date='02-01'
        )
        self.layer.features.create(
            geom = self.fake_geometry,
            properties = {},
            from_date='04-01',
            to_date='05-01'
        )
        self.layer.features.create(
            geom = self.fake_geometry,
            properties = {},
            from_date='01-01',
            to_date='03-01'
        )
        self.layer.features.create(
            geom = self.fake_geometry,
            properties = {},
            from_date='10-01',
            to_date='12-31'
        )
        self.layer.features.create(
            geom = self.fake_geometry,
            properties = {},
            from_date='01-20',
            to_date='12-20'
        )

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
