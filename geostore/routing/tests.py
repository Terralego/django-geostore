from django.contrib.gis.geos import LineString, Point
from django.db import connection
from django.test import override_settings, TestCase, tag
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from unittest import mock

from geostore.models import Feature, Layer
from geostore.routing.helpers import Routing, RoutingException
from .. import settings as app_settings
from ..tests.factories import FeatureFactory, UserFactory
from ..tests.utils import get_files_tests


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

        self.assertTrue(Routing.create_topology(self.layer, tolerance=0.0001))

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
                                    {'geom': geometry.geojson})
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

    def test_routing_update_view(self):
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

    @mock.patch('geostore.settings.GEOSTORE_ROUTING_CELERY_ASYNC', new_callable=mock.PropertyMock)
    @mock.patch('geostore.routing.signals.execute_async_func')
    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_remove_geom_update_routing(self, mock_async, mock_routing):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        mock_routing.return_value = True
        points = [Point(
            *point['coordinates'],
            srid=app_settings.INTERNAL_GEOMETRY_SRID) for point in self.points]

        geometry = LineString(*points)
        old_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, old_response.status_code)
        old_json = old_response.json()
        old_features = old_json.get('route').get('features')
        first_id = old_features[0]['properties']['id']
        id_new_features = [feature['properties']['id'] for feature in old_features]
        self.assertIn(first_id, id_new_features)

        feature = Feature.objects.get(id=first_id)
        feature.delete()

        new_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, new_response.status_code)
        new_json = new_response.json()
        self.assertNotEqual(old_json, new_json)
        id_new_features = [feature['properties']['id'] for feature in new_json.get('route').get('features')]
        self.assertNotIn(first_id, id_new_features)

    @mock.patch('geostore.settings.GEOSTORE_ROUTING_CELERY_ASYNC', new_callable=mock.PropertyMock)
    @mock.patch('geostore.routing.signals.execute_async_func')
    @override_settings(CELERY_ALWAYS_EAGER=False)
    def test_update_geom_update_routing(self, mock_async, mock_routing):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        mock_routing.return_value = True
        points = [Point(
            *point['coordinates'],
            srid=app_settings.INTERNAL_GEOMETRY_SRID) for point in self.points]

        geometry = LineString(*points)
        old_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, old_response.status_code)
        old_json = old_response.json()
        old_features = old_json.get('route').get('features')
        first_id = old_features[0]['properties']['id']
        id_new_features = [feature['properties']['id'] for feature in old_features]
        self.assertIn(first_id, id_new_features)

        feature = Feature.objects.get(id=first_id)
        feature.geom = LineString((1.3, 43.5), (1.32, 43.5))
        feature.save()

        new_response = self.client.post(reverse('layer-route',
                                                args=[self.layer.pk]),
                                        {'geom': geometry.geojson})
        self.assertEqual(HTTP_200_OK, new_response.status_code)
        new_json = new_response.json()
        self.assertNotEqual(old_json, new_json)
        id_new_features = [feature['properties']['id'] for feature in new_json.get('route').get('features')]
        self.assertNotIn(first_id, id_new_features)
