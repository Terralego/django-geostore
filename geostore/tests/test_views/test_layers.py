import json
import factory.random
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest import skipIf
from zipfile import ZipFile

from django.contrib.auth.models import Permission
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN)
from rest_framework.test import APITestCase

from geostore import GeometryTypes
from geostore import settings as app_settings
from geostore.import_export.helpers import get_serialized_properties
from geostore.models import Feature, LayerGroup
from geostore.tests.factories import (FeatureFactory, LayerFactory, SuperUserFactory,
                                      UserFactory)
from geostore.tests.utils import get_files_tests


class LayerLineIntersectionTestCase(APITestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory(permissions=[])
        self.client.force_authenticate(user=self.user)

    def test_intersect_bad_geometry(self):
        linestring = {
            "type": "LineString",
            "coordinates": [
                [
                    [1.25, 5.5, [2.65, 5.5]]
                ]
            ]
        }
        response = self.client.post(
            reverse('layer-intersects', kwargs={'pk': self.layer.pk}),
            {'geom': json.dumps(linestring)},
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)


class LayerPolygonIntersectTestCase(APITestCase):
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
        self.user = UserFactory()
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
            reverse('layer-intersects', kwargs={'pk': layer.pk}),
            {'geom': json.dumps(self.polygon)},
            format='json',
        )
        self.assertEqual(HTTP_200_OK, response.status_code)
        json_response = response.json()
        self.assertEqual(
            2,
            len(json_response['results']['features'])
        )


class LayerFeatureIntersectionTest(APITestCase):
    def setUp(self):
        self.fake_geometry = {
            "type": "Point",
            "coordinates": [
                2.,
                45.
            ]
        }
        self.intersect_geometry = {
            "type": "LineString",
            "coordinates": [
                [
                    1.3839340209960938,
                    43.602521593464054
                ],
                [
                    1.4869308471679688,
                    43.60376465190968
                ]
            ]
        }
        self.intersect_ref_geometry = {
            "type": "LineString",
            "coordinates": [
                [
                    1.440925598144531,
                    43.64750394449096
                ],
                [
                    1.440582275390625,
                    43.574421623084234
                ]
            ]
        }
        self.fake_linestring = {
            "type": "LineString",
            "coordinates": [
                [
                    1.3839340209960938,
                    43.602521593464054
                ],
            ]
        }
        self.fake_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        1.3839340209960938,
                        43.602521593464054
                    ],
                    [
                        1.440582275390625,
                        43.574421623084234
                    ]
                ]
            ]
        }

        self.layer = LayerFactory.create(add_features=5)
        self.group = LayerGroup.objects.create(name='mygroup', slug='mygroup')
        self.group.layers.add(self.layer)

        self.user = UserFactory()
        self.client.force_authenticate(self.user)

    def test_features_intersections(self):
        layer = LayerFactory()
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.intersect_ref_geometry)))

        """The layer below must intersect"""
        response = self.client.post(
            reverse('layer-intersects', args=[layer.pk, ]),
            {
                'geom': json.dumps(self.intersect_geometry)
            }
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json().get('results', {})
        self.assertEqual(
            1,
            len(response.get('features'))
        )
        self.assertDictEqual(
            self.intersect_ref_geometry,
            response.get('features')[0].get('geometry')
        )

        """The layer below must NOT intersect"""
        response = self.client.post(
            reverse('layer-intersects', args=[layer.name, ]),
            {
                'geom': json.dumps(self.fake_geometry)
            }
        )

        self.assertEqual(HTTP_200_OK, response.status_code)

        response = response.json().get('results', {})
        self.assertEqual(0, len(response.get('features')))

        """Tests that the intersects view throw an error if geometry is
           invalid
        """
        response = self.client.post(
            reverse('layer-intersects', args=[layer.pk, ]),
            {
                'geom': '''Invalid geometry'''
            }
        )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_features_linestring_format(self):
        response = self.client.post(
            reverse('layer-intersects', args=[self.layer.pk, ]),
            {
                'geom': json.dumps(self.fake_linestring)
            }
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_features_polygon_format(self):
        response = self.client.post(
            reverse('layer-intersects', args=[self.layer.pk, ]),
            {
                'geom': json.dumps(self.fake_polygon)
            }
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
class LayerShapefileTestCase(APITestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = SuperUserFactory()
        self.client.force_authenticate(self.user)

    def test_shapefile_export(self):
        # Create at least one feature in the layer, so it's not empty
        FeatureFactory(layer=self.layer)

        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_200_OK, response.status_code)

        zip_file = ZipFile(BytesIO(response.content), 'r')
        self.assertListEqual(
            sorted(['prj', 'cpg', 'shx', 'shp', 'dbf']),
            sorted(set([f.split('.')[1] for f in zip_file.namelist()]))
        )

    def test_properties_serializations(self):
        layer = LayerFactory()
        test_properties = {
            'int': 42,
            'str': 'test string',
            'dict': {
                'a': 'b',
            }
        }

        serialized_properties = get_serialized_properties(layer, test_properties)
        self.assertEqual(serialized_properties['str'], test_properties['str'])
        self.assertIsInstance(serialized_properties['int'], str)
        self.assertIsInstance(serialized_properties['dict'], str)

    def test_shapefile_same_import_export(self):
        FeatureFactory(layer=self.layer, properties={
            'key1': [{
                'key3': 'hello world',
            }]
        })

        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_200_OK, response.status_code)

        shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                       response.content)
        new_layer = LayerFactory()
        response = self.client.post(
            reverse('layer-shapefile', args=[new_layer.pk, ]),
            {'shapefile': shapefile, }, format="multipart"
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(self.layer.features.first().properties,
                         new_layer.features.first().properties)

    def test_empty_shapefile_export(self):
        # Create en empty layer to test its behavior
        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_204_NO_CONTENT, response.status_code)

    def test_no_shapefile_import(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        layer = LayerFactory()

        response = self.client.post(
            reverse('layer-shapefile', args=[layer.pk, ]), )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_shapefile_import_view(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        layer = LayerFactory()

        shapefile_path = get_files_tests('shapefile-WGS84.zip')

        with open(shapefile_path, 'rb') as fd:
            shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                           fd.read())

            response = self.client.post(
                reverse('layer-shapefile', args=[layer.pk, ]),
                {'shapefile': shapefile, }, format='multipart'
            )

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(8, layer.features.all().count())

    def test_shapefile_import_view_error(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                       b'bad bad data')

        response = self.client.post(
            reverse('layer-shapefile', args=[self.layer.pk, ]),
            {'shapefile': shapefile, }
        )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)


class LayerAPITestCase(APITestCase):
    geometry = {
        "type": "LineString",
        "coordinates": [
            [
                1.3839340209960938,
                43.602521593464054
            ], [
                1.4869308471679688,
                43.60376465190968
            ]
        ]
    }

    @classmethod
    def setUpTestData(cls):
        cls.layer = LayerFactory()
        cls.layer_group = LayerGroup.objects.create(name='layer group')
        cls.layer_group.layers.add(cls.layer)
        cls.user = UserFactory()

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_patch_no_permission(self):
        FeatureFactory(layer=self.layer, properties={'a': 'b'})

        response = self.client.patch(
            reverse('layer-detail', args=[self.layer.name, ]), {})

        self.assertEqual(HTTP_403_FORBIDDEN, response.status_code)

    def test_patch_permission_ok(self):
        user = UserFactory()
        user.user_permissions.add(
            Permission.objects.get(codename='can_manage_layers')
        )
        self.client.force_authenticate(user)
        geom = GEOSGeometry(json.dumps(self.geometry))
        feature = FeatureFactory(layer=self.layer,
                                 geom=geom,
                                 properties={'a': 'b'})

        updated_properties = {
            'c': 'd',
            'a': 'd',
        }

        response = self.client.patch(
            reverse('layer-detail', args=[self.layer.name, ]),
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        'geometry': self.geometry,
                        'properties': updated_properties,
                    },
                ]
            }, format='json')

        self.assertEqual(HTTP_200_OK, response.status_code, response.content)
        response = response.json()
        self.assertEqual(
            response['features'][0]['properties'],
            updated_properties
        )

        feature.refresh_from_db()
        self.assertDictEqual(feature.properties, updated_properties)

    @skipIf(not app_settings.GEOSTORE_EXPORT_CELERY_ASYNC, 'Test with export async only')
    def test_async_exports_links(self):
        response = self.client.get(reverse('layer-detail', args=[self.layer.name, ]),)
        self.assertEqual(HTTP_200_OK, response.status_code)
        data = response.json()
        self.assertEqual(data['async_exports'],
                         {"GeoJSON": "/api/layer/{}/geojson/".format(self.layer.pk),
                          "KML": "/api/layer/{}/kml/".format(self.layer.pk),
                          'Shape': '/api/layer/{}/shapefile_async/'.format(self.layer.pk)})

    def test_layer_extent_null(self):
        response = self.client.get(reverse('layer-extent', args=[self.layer.name, ]),)
        self.assertEqual(HTTP_200_OK, response.status_code)
        data = response.json()
        self.assertEqual(data['extent'], None)

    def test_layer_extent_not_null(self):
        geom = GEOSGeometry(json.dumps(self.geometry))
        FeatureFactory(layer=self.layer,
                       geom=geom,
                       properties={'a': 'b'})
        response = self.client.get(reverse('layer-extent', args=[self.layer.name, ]), )
        self.assertEqual(HTTP_200_OK, response.status_code)
        data = response.json()
        self.assertAlmostEqual(data['extent'][0], self.geometry["coordinates"][0][0])
        self.assertAlmostEqual(data['extent'][1], self.geometry["coordinates"][0][1])
        self.assertAlmostEqual(data['extent'][2], self.geometry["coordinates"][1][0])
        self.assertAlmostEqual(data['extent'][3], self.geometry["coordinates"][1][1])


class LayerCreationTest(APITestCase):
    def setUp(self):
        self.user = UserFactory(permissions=['geostore.can_manage_layers', ])
        self.client.force_authenticate(user=self.user)

        self.point_layer = LayerFactory(name="no schema point geom",
                                        geom_type=GeometryTypes.Point)
        self.null_layer = LayerFactory(name="no schema null geom", geom_type=None)

    def test_point_layer_allow_point(self):
        response = self.client.post(reverse('feature-list', args=[self.point_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

    def test_point_layer_disallow_other(self):
        response = self.client.post(reverse('feature-list', args=[self.point_layer.pk, ]),
                                    data={"geom": "LINESTRING(0 0, 1 1)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST, response.json())

    def test_null_layer_allow_points(self):
        response = self.client.post(reverse('feature-list', args=[self.null_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

    def test_null_layer_allow_linestring(self):
        response = self.client.post(reverse('feature-list', args=[self.null_layer.pk, ]),
                                    data={"geom": "LINESTRING(0 0, 1 1)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())


class LayerPropertyValuesTest(APITestCase):
    def setUp(self):
        self.user = SuperUserFactory()
        self.client.force_authenticate(user=self.user)

        factory.random.reseed_random(42)

        self.layer = LayerFactory.create(add_random_features=20)

    def test_property_values(self):
        response = self.client.get(
            reverse(
                "layer-property-values",
                args=[
                    self.layer.pk,
                ],
            ),
            {"property": "country"},
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertEqual(
            response, ["Alaska", "Cameroun", "Canada", "France", "Groland"]
        )

    def test_property_no_values(self):
        response = self.client.get(
            reverse(
                "layer-property-values",
                args=[
                    self.layer.pk,
                ],
            ),
            {"property": "non_existing"},
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertEqual(response, [None])

    def test_property_values_with_empty(self):

        response = self.client.get(
            reverse(
                "layer-property-values",
                args=[
                    self.layer.pk,
                ],
            ),
            {"property": "status"},
        )

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()

        self.assertEqual(response, [None, "", "Employed", "Unemployed"])

    def test_property_values_missing_param(self):

        response = self.client.get(
            reverse(
                "layer-property-values",
                args=[
                    self.layer.pk,
                ],
            ),
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)
