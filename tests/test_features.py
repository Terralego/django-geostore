from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .factories import LayerFactory, FeatureFactory, TerraUserFactory


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
        response = self.client.get(reverse('layer-geojson', args=[self.layer.pk]))
        self.assertEqual(200, response.status_code)

        response = response.json()
        self.assertEqual('FeatureCollection', response.get('type'))
        self.assertEqual(self.layer.features.all().count(), len(response.get('features')))
        