import os

from django.contrib.gis.geos import GEOSGeometry, LineString, Point
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from terracommon.accounts.tests.factories import TerraUserFactory
from terracommon.terra.models import Layer
from terracommon.terra.tiles.helpers import Routing


class RoutingTestCase(TestCase):
    points = [
        {
          "type": "Point",
          "coordinates": [
            1.4534568786621094,
            43.622127847162005
          ]
        }, {
          "type": "Point",
          "coordinates": [
            1.4556884765625,
            43.61839973326468
          ]
        }, {
          "type": "Point",
          "coordinates": [
            1.4647650718688965,
            43.61916090863259
          ]
        }
    ]

    def setUp(self):
        self.layer = Layer.objects.create(name='test_layer')
        self.user = TerraUserFactory()
        self.client.force_login(self.user)

        geojson_path = os.path.join(
                          os.path.dirname(__file__),
                          'files',
                          'toulouse.geojson')

        with open(geojson_path,
                  mode='r',
                  encoding="utf-8") as geojson:
            self.layer.from_geojson(geojson.read())

        Routing.create_topology(self.layer)

    def test_topology(self):
        self.assertTrue(Routing.create_topology(self.layer))

    def test_points_in_line(self):
        routing = Routing(
          [Point(*p['coordinates'], srid=4326) for p in self.points],
          self.layer)

        self.assertIsInstance(routing.get_route(), GEOSGeometry)

    def test_routing_view_bad_geometry(self):
        response = self.client.post(
          reverse('layer-route', args=[self.layer.pk]))

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

        bad_geometry = Point((1, 1))
        response = self.client.post(
          reverse('layer-route', args=[self.layer.pk]),
          {'geom': bad_geometry.geojson, }
        )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_routing_view(self):

        geometry = LineString(*[Point(*point['coordinates'], srid=4326)
                                for point in self.points])

        response = self.client.post(
          reverse('layer-route', args=[self.layer.pk]),
          {'geom': geometry.geojson, }
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertIsInstance(GEOSGeometry(response), LineString)
