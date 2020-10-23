from django.contrib.gis.geos import LineString, Point
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import override_settings, TestCase, tag
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from unittest import mock

from geostore import GeometryTypes
from geostore.models import Feature, Layer
from geostore.routing.helpers import Routing, RoutingException
from geostore import settings as app_settings
from geostore.tests.factories import FeatureFactory, UserFactory
from geostore.tests.utils import get_files_tests


@tag("routing")
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
        self.layer = Layer.objects.create(name='test_layer', routable=True)
        self.user = UserFactory(is_superuser=True)
        self.client.force_login(self.user)

        geojson_path = get_files_tests('toulouse.geojson')

        with open(geojson_path,
                  mode='r',
                  encoding="utf-8") as geojson:
            self.layer.from_geojson(geojson.read())

        self.assertTrue(Routing.update_topology(self.layer, tolerance=0.0001))

    def test_points_in_line(self):
        routing = Routing(
            [Point(*p['coordinates'],
                   srid=app_settings.INTERNAL_GEOMETRY_SRID) for p in self.points
             ],
            self.layer)

        self.assertIsInstance(routing.get_route(), dict)

    def test_routing_view_bad_geometry(self):
        response = self.client.post(reverse('layer-route',
                                            args=[self.layer.pk]))

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code, response.json())

        bad_geometry = Point((1, 1))
        response = self.client.post(reverse('layer-route',
                                            args=[self.layer.pk]),
                                    {'geom': bad_geometry.geojson, })
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_routing_view(self):
        points = [Point(
            *point['coordinates'],
            srid=app_settings.INTERNAL_GEOMETRY_SRID) for point in self.points]

        geometry = LineString(*points)

        response = self.client.post(reverse('layer-route',
                                            args=[self.layer.pk]),
                                    {'geom': geometry.geojson, })

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertEqual(response.get('route').get('type'), 'FeatureCollection')
        self.assertTrue(len(response.get('route').get('features')) >= 2)

        # Ensure End Points are close to requested points
        start = Point(*response.get('route').get('features')[0].get('geometry')
                      .get('coordinates')[0])
        end = Point(*response.get('route').get('features')[-1].get('geometry')
                    .get('coordinates')[-1])
        self.assertTrue(points[0].distance(start) <= 0.001)
        self.assertTrue(points[-1].distance(end) <= 0.001)

    def test_routing_view_edge_case(self):
        points = [Point(
            *p['coordinates'],
            srid=app_settings.INTERNAL_GEOMETRY_SRID) for p in
            [self.points[0], self.points[0]]]

        geometry = LineString(*points)

        response = self.client.post(reverse('layer-route',
                                            args=[self.layer.pk]),
                                    {'geom': geometry.geojson, })
        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()
        self.assertEqual(response.get('route').get('type'), 'FeatureCollection')
        self.assertTrue(len(response.get('route').get('features')) >= 1)

        # Ensure End Points are close to requested points
        start = Point(*response.get('route').get('features')[0].get('geometry')
                      .get('coordinates'))
        end = Point(*response.get('route').get('features')[-1].get('geometry')
                    .get('coordinates'))
        self.assertTrue(points[0].distance(start) <= 0.001)
        self.assertTrue(points[-1].distance(end) <= 0.001)

    def test_routing_cache(self):
        geometry = LineString(*[Point(
            *point['coordinates'],
            srid=app_settings.INTERNAL_GEOMETRY_SRID) for point in self.points])
        with self.settings(DEBUG=True,
                           CACHES={'default': {
                               'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
                           }):

            self.client.post(reverse('layer-route',
                                     args=[self.layer.pk]),
                             {'geom': geometry.geojson, })

            initial_count = len(connection.queries)
            counts = []
            for x in range(2):
                self.client.post(
                    reverse('layer-route', args=[self.layer.pk]),
                    {'geom': geometry.geojson, }
                )

                counts.append(len(connection.queries))

            self.assertTrue(all([counts[0] == c for c in counts]))
            self.assertTrue(all([initial_count > c for c in counts]))

    def test_layer_with_polygon(self):
        """test that a layer with another kind of geometry raise the right exception"""
        feature = FeatureFactory()

        with self.assertRaises(RoutingException):
            Routing(self.points, feature.layer)

    def test_routable_point(self):
        self.layer.geom_type = GeometryTypes.Point
        with self.assertRaisesRegex(ValidationError, 'Invalid geom type for routing'):
            self.layer.clean()

    def test_routable_linestring(self):
        self.layer.geom_type = GeometryTypes.LineString
        self.layer.clean()
        self.assertEqual(self.layer.geom_type, GeometryTypes.LineString)
        self.assertEqual(self.layer.routable, True)


@tag("routing")
class UpdateTopologyTestCase(TestCase):
    points = [Point(0, 40, srid=app_settings.INTERNAL_GEOMETRY_SRID),
              Point(10, 40, srid=app_settings.INTERNAL_GEOMETRY_SRID)]

    def setUp(self):
        self.layer = Layer.objects.create(name='test_layer', routable=True)
        self.user = UserFactory(is_superuser=True)
        self.client.force_login(self.user)
        self.other_feature = Feature.objects.create(layer=self.layer, geom="SRID=4326;LINESTRING(5 40, 6 40)")
        self.feature1 = Feature.objects.create(layer=self.layer, geom="SRID=4326;LINESTRING(0 40, 1 40)")
        self.feature2 = Feature.objects.create(layer=self.layer, geom="SRID=4326;LINESTRING(1 40, 9 40)")
        self.feature3 = Feature.objects.create(layer=self.layer, geom="SRID=4326;LINESTRING(9 40, 10 40)")
        self.feature4 = Feature.objects.create(layer=self.layer, geom="SRID=4326;LINESTRING(1 40, 1 41, 9 41, 9 40)")
        self.assertTrue(Routing.update_topology(self.layer, tolerance=0.0001))

    @mock.patch('geostore.settings.GEOSTORE_ROUTING_CELERY_ASYNC', new_callable=mock.PropertyMock)
    @mock.patch('geostore.routing.signals.execute_async_func')
    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_remove_geom_update_routing(self, mock_async, mock_routing):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        mock_routing.return_value = True

        geometry = LineString(self.points, srid=app_settings.INTERNAL_GEOMETRY_SRID)
        old_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, old_response.status_code)
        old_json = old_response.json()
        old_features = old_json.get('route').get('features')
        first_id = self.feature3.pk
        id_new_features = [feature['properties']['id'] for feature in old_features]
        self.assertIn(first_id, id_new_features)

        self.feature3.delete()

        new_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, new_response.status_code)
        new_json = new_response.json()
        self.assertNotEqual(old_json, new_json)
        id_new_features = [feature['properties']['id'] for feature in new_json.get('route').get('features')]
        self.assertNotIn(first_id, id_new_features)
        self.assertNotIn(self.other_feature.pk, id_new_features)

    @mock.patch('geostore.settings.GEOSTORE_ROUTING_CELERY_ASYNC', new_callable=mock.PropertyMock)
    @mock.patch('geostore.routing.signals.execute_async_func')
    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_update_geom_update_routing(self, mock_async, mock_routing):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        mock_routing.return_value = True

        geometry = LineString(self.points, srid=app_settings.INTERNAL_GEOMETRY_SRID)
        old_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, old_response.status_code)
        old_json = old_response.json()
        old_features = old_json.get('route').get('features')
        first_id = self.feature3.pk
        id_new_features = [feature['properties']['id'] for feature in old_features]
        self.assertIn(first_id, id_new_features)

        self.feature3.geom = LineString((1, 40), (1, 38), (9, 38), (9, 40))
        self.feature3.save()

        new_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, new_response.status_code)
        new_json = new_response.json()
        self.assertNotEqual(old_json, new_json)
        id_new_features = [feature['properties']['id'] for feature in new_json.get('route').get('features')]
        self.assertNotIn(first_id, id_new_features)
        self.assertNotIn(self.other_feature.pk, id_new_features)
