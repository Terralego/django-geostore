from django.conf import settings
from django.contrib.gis.geos import LineString, Point
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from terracommon.accounts.tests.factories import TerraUserFactory
from terracommon.terra.models import Layer
from terracommon.terra.routing.helpers import Routing
from terracommon.terra.tests.factories import FeatureFactory
from terracommon.terra.tests.utils import get_files_tests


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

        geojson_path = get_files_tests('toulouse.geojson')

        with open(geojson_path,
                  mode='r',
                  encoding="utf-8") as geojson:
            self.layer.from_geojson(geojson.read())

        self.assertTrue(Routing.create_topology(self.layer))

    def test_points_in_line(self):
        routing = Routing(
          [Point(
            *p['coordinates'],
            srid=settings.INTERNAL_GEOMETRY_SRID) for p in self.points],
          self.layer)

        self.assertIsInstance(routing.get_route(), dict)

    def test_routing_view_bad_geometry(self):
        response = self.client.post(
          reverse('terra:layer-route', args=[self.layer.pk]))

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

        bad_geometry = Point((1, 1))
        response = self.client.post(
          reverse('terra:layer-route', args=[self.layer.pk]),
          {'geom': bad_geometry.geojson, }
        )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_routing_view(self):
        points = [Point(
            *point['coordinates'],
            srid=settings.INTERNAL_GEOMETRY_SRID) for point in self.points]

        geometry = LineString(*points)

        response = self.client.post(
          reverse('terra:layer-route', args=[self.layer.pk]),
          {'geom': geometry.geojson, }
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertEqual(response.get('geom').get('type'), 'FeatureCollection')
        self.assertTrue(len(response.get('geom').get('features')) >= 2)

        # Ensure End Points are close to requested points
        start = Point(*response.get('geom').get('features')[0].get('geometry')
                      .get('coordinates')[0])
        end = Point(*response.get('geom').get('features')[-1].get('geometry')
                    .get('coordinates')[-1])
        self.assertTrue(points[0].distance(start) <= 0.001)
        self.assertTrue(points[-1].distance(end) <= 0.001)

    def test_routing_view_edge_case(self):
        points = [Point(
            *p['coordinates'],
            srid=settings.INTERNAL_GEOMETRY_SRID) for p in
            [self.points[0], self.points[0]]]

        geometry = LineString(*points)

        response = self.client.post(
          reverse('terra:layer-route', args=[self.layer.pk]),
          {'geom': geometry.geojson, }
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertEqual(response.get('geom').get('type'), 'FeatureCollection')
        self.assertTrue(len(response.get('geom').get('features')) >= 1)

        # Ensure End Points are close to requested points
        start = Point(*response.get('geom').get('features')[0].get('geometry')
                      .get('coordinates'))
        end = Point(*response.get('geom').get('features')[-1].get('geometry')
                    .get('coordinates'))
        self.assertTrue(points[0].distance(start) <= 0.001)
        self.assertTrue(points[-1].distance(end) <= 0.001)

    def test_routing_cache(self):
        geometry = LineString(*[Point(
            *point['coordinates'],
            srid=settings.INTERNAL_GEOMETRY_SRID) for point in self.points])

        with self.settings(DEBUG=True,
                           CACHES={
                               'default': {
                                   'BACKEND': ('django.core.cache.backends'
                                               '.locmem.LocMemCache')
                                }}):

            self.client.post(
                reverse('terra:layer-route', args=[self.layer.pk]),
                {'geom': geometry.geojson, }
            )

            initial_count = len(connection.queries)
            counts = []
            for x in range(2):
                self.client.post(
                    reverse('terra:layer-route', args=[self.layer.pk]),
                    {'geom': geometry.geojson, }
                )

                counts.append(len(connection.queries))

            self.assertTrue(all([counts[0] == c for c in counts]))
            self.assertTrue(all([initial_count > c for c in counts]))

    def test_layer_with_polygon(self):
        # test that a layer with another kind of geometry raise the right
        # exception

        feature = FeatureFactory()
        with self.assertRaises(ValueError):
            Routing(self.points, feature.layer)
