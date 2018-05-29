from django.test import TestCase
from django.urls import reverse

from .factories import LayerFactory


class VectorTilesTestCase(TestCase):
    def test_vector_tiles_view(self):
        layer = LayerFactory()

        layer.from_geojson(
            from_date='01-01',
            to_date='12-31',
            geojson_data='''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                    [
                        1.3700294494628906,
                        43.603640347220924
                    ],
                    [
                        1.2984466552734375,
                        43.57902295875415
                    ]
                    ]
                }
                }
            ]
            }
        ''')
        response = self.client.get(reverse('layer-tiles',
                                           args=[layer.pk, 13, 4126, 2991]))
        self.assertEqual(200, response.status_code)
        self.assertGreater(len(response.content), 0)

        response = self.client.get(reverse('layer-tiles',
                                           args=[layer.pk, 1, 1, 1]))
        self.assertEqual(404, response.status_code)
