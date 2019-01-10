import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APIClient

from terracommon.accounts.tests.factories import TerraUserFactory
from terracommon.terra.models import Feature
from terracommon.terra.tests.factories import LayerFactory


class PolygonIntersectTestCase(TestCase):
    def setUp(self):
        # from http://wiki.geojson.org/GeoJSON_draft_version_6#Polygon
        self.polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [100.0, 0.0],
                    [101.0, 0.0],
                    [101.0, 1.0],
                    [100.0, 1.0],
                    [100.0, 0.0]
                ]
            ]
        }
        self.client = APIClient()
        self.user = TerraUserFactory()
        self.client.force_authenticate(user=self.user)

    def test_polygon_intersection(self):
        layer = LayerFactory()
        Feature.objects.create(
            geom=json.dumps({
                "type": "LineString",
                "coordinates": [
                    [103.0, 0.0], [101.0, 1.0]
                ]
            }),
            layer=layer,
            properties={},
        )
        Feature.objects.create(
            geom=json.dumps({
                "type": "Point",
                "coordinates": [100.0, 0.0]
            }),
            layer=layer,
            properties={},
        )

        # This feature is not intersecting with the polygon
        # It is not expected to be in the response returned
        Feature.objects.create(
            geom=json.dumps({
                "type": "LineString",
                "coordinates": [
                    [30, 10], [10, 30], [40, 40]
                ]
            }),
            layer=layer,
            properties={},
        )

        response = self.client.post(
            reverse('terra:layer-intersects', kwargs={'pk': layer.pk}),
            {'geom': json.dumps(self.polygon)},
            format='json',
        )
        self.assertEqual(HTTP_200_OK, response.status_code)
        json_response = response.json()
        self.assertEqual(
            2,
            len(json_response['results']['features'])
        )
