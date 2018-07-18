import os

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tiles.helpers import Routing


class RoutingTestCasse(TestCase):

    def setUp(self):
        self.layer = Layer.objects.create(name='test_layer')
        geojson_path = os.path.join(
                          os.path.dirname(__file__),
                          'files',
                          'toulouse.geojson'),
        with open(geojson_path,
                  mode='r',
                  encoding="utf-8") as geojson:
            self.layer.from_geojson(geojson.read())

        Routing.create_topology(self.layer)

    def test_topology(self):
        self.assertTrue(Routing.create_topology(self.layer))

    def test_points_in_line(self):
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

        routing = Routing(points, self.layer)

        self.assertIsInstance(routing.get_route(), GEOSGeometry)
