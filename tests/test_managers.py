import json
from datetime import date

from django.test import TestCase

from .factories import FeatureFactory, LayerFactory


class ManagersTestCase(TestCase):
    point_geom = {
        "type": "Point",
        "coordinates": [
            1.67266845703125,
            43.65396273281939
        ]
    }

    def test_for_date(self):
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
                geom=json.dumps(self.point_geom),
                **feature
            )

        periods = (
            (date(2018, 1, 5), date(2018, 2, 5), 3),
            (date(2018, 4, 1), date(2018, 5, 1), 1),
            (date(2018, 8, 30), date(2018, 10, 10), 2),
            (date(2018, 11, 10), date(2018, 12, 10), 1),
        )

        for from_date, to_date, count in periods:
            self.assertEqual(
                count,
                layer.features.for_date(from_date, to_date).count()
                )
