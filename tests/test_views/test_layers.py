import json
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import Permission
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN)
from rest_framework.test import APIClient

from terracommon.terra import GeometryTypes
from terracommon.terra.models import Feature
from terracommon.terra.tests.factories import (FeatureFactory, LayerFactory,
                                               UserFactory)
from terracommon.terra.tests.utils import get_files_tests


class LayerLineIntersectionTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.client = APIClient()
        self.user = UserFactory()
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
            reverse('terra:layer-intersects', kwargs={'pk': self.layer.pk}),
            {'geom': json.dumps(linestring)},
            format='json',
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)


class LayerPolygonIntersectTestCase(TestCase):
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


class LayerFeatureIntersectionTest(TestCase):
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

        self.group_name = 'mygroup'
        self.layer = LayerFactory.create(group=self.group_name,
                                         add_features=5)

        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_features_intersections(self):
        layer = LayerFactory(group=self.group_name)
        FeatureFactory(
            layer=layer,
            geom=GEOSGeometry(json.dumps(self.intersect_ref_geometry)))

        """The layer below must intersect"""
        response = self.client.post(
            reverse('terra:layer-intersects', args=[layer.pk, ]),
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
            reverse('terra:layer-intersects', args=[layer.name, ]),
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
            reverse('terra:layer-intersects', args=[layer.pk, ]),
            {
                'geom': '''Invalid geometry'''
            }
        )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_features_linestring_format(self):
        response = self.client.post(
            reverse('terra:layer-intersects', args=[self.layer.pk, ]),
            {
                'geom': json.dumps(self.fake_linestring)
            }
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_features_polygon_format(self):
        response = self.client.post(
            reverse('terra:layer-intersects', args=[self.layer.pk, ]),
            {
                'geom': json.dumps(self.fake_polygon)
            }
        )

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)


class LayerShapefileTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_shapefile_export(self):
        # Create at least one feature in the layer, so it's not empty
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        FeatureFactory(layer=self.layer)

        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_200_OK, response.status_code)

        zip = ZipFile(BytesIO(response.content), 'r')
        self.assertListEqual(
            sorted(['prj', 'cpg', 'shx', 'shp', 'dbf']),
            sorted([f.split('.')[1] for f in zip.namelist()])
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

        serialized_properties = layer._get_serialized_properties(test_properties)
        self.assertEqual(serialized_properties['str'], test_properties['str'])
        self.assertIsInstance(serialized_properties['int'], str)
        self.assertIsInstance(serialized_properties['dict'], str)

    def test_shapefile_same_import_export(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        FeatureFactory(layer=self.layer, properties={
            'key1': [{
                'key3': 'hello world',
            }]
        })

        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_200_OK, response.status_code)

        shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                       response.content)
        new_layer = LayerFactory()
        response = self.client.post(
                reverse('terra:layer-shapefile', args=[new_layer.pk, ]),
                {'shapefile': shapefile, }
                )

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(self.layer.features.first().properties,
                         new_layer.features.first().properties)

    def test_empty_shapefile_export(self):
        # Create en ampty layer to test its behavior
        LayerFactory()
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_204_NO_CONTENT, response.status_code)

    def test_shapefile_no_permission(self):
        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])

        self.assertEqual(
            self.client.get(shape_url).status_code,
            HTTP_403_FORBIDDEN
        )

    def test_no_shapefile_import(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        layer = LayerFactory()

        response = self.client.post(
            reverse('terra:layer-shapefile', args=[layer.pk, ]),)

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_shapefile_import_view(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        layer = LayerFactory()

        shapefile_path = get_files_tests('shapefile-WGS84.zip')

        with open(shapefile_path, 'rb') as fd:
            shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                           fd.read())

            response = self.client.post(
                reverse('terra:layer-shapefile', args=[layer.pk, ]),
                {'shapefile': shapefile, }
                )

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(8, layer.features.all().count())

    def test_shapefile_import_view_error(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_import_layers'))
        shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                       b'bad bad data')

        response = self.client.post(
            reverse('terra:layer-shapefile', args=[self.layer.pk, ]),
            {'shapefile': shapefile, }
            )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)


class LayerGeojsonTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_to_geojson(self):
        # Create at least one feature in the layer, so it's not empty
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        FeatureFactory(layer=self.layer)

        geojson_url = reverse('terra:layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(geojson_url)

        self.assertEqual(HTTP_200_OK, response.status_code)

        response = response.json()
        self.assertEqual('FeatureCollection', response.get('type'))
        self.assertEqual(self.layer.features.all().count(),
                         len(response.get('features')))

    def test_to_geojson_no_permission(self):
        # Create at least one feature in the layer, so it's not empty
        FeatureFactory(layer=self.layer)

        geojson_url = reverse('terra:layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(geojson_url)

        self.assertEqual(HTTP_403_FORBIDDEN, response.status_code)


class LayerDetailTest(TestCase):
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

    def setUp(self):
        self.client = APIClient()
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

    def test_no_permission(self):

        FeatureFactory(layer=self.layer, properties={'a': 'b'})

        response = self.client.patch(
            reverse('terra:layer-detail', args=[self.layer.name, ]), {})

        self.assertEqual(HTTP_403_FORBIDDEN, response.status_code)

    def test_update(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='can_update_features_properties')
        )
        geom = GEOSGeometry(json.dumps(self.geometry))
        feature = FeatureFactory(layer=self.layer,
                                 geom=geom,
                                 properties={'a': 'b'})

        updated_properties = {
            'c': 'd',
            'a': 'd',
            }

        response = self.client.patch(
            reverse('terra:layer-detail', args=[self.layer.name, ]),
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

        self.assertEqual(HTTP_200_OK, response.status_code)
        response = response.json()
        self.assertEqual(
            response['features'][0]['properties'],
            updated_properties
            )

        feature.refresh_from_db()
        self.assertDictEqual(feature.properties, updated_properties)


class LayerCreationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

        self.point_layer = LayerFactory(name="no schema point geom",
                                        geom_type=GeometryTypes.Point)
        self.null_layer = LayerFactory(name="no schema null geom", geom_type=None)

    def test_point_layer_allow_point(self):
        response = self.client.post(reverse('terra:feature-list', args=[self.point_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

    def test_point_layer_disallow_other(self):
        response = self.client.post(reverse('terra:feature-list', args=[self.point_layer.pk, ]),
                                    data={"geom": "LINESTRING(0 0, 1 1)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST, response.json())

    def test_null_layer_allow_points(self):
        response = self.client.post(reverse('terra:feature-list', args=[self.null_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

    def test_null_layer_allow_linestring(self):
        response = self.client.post(reverse('terra:feature-list', args=[self.null_layer.pk, ]),
                                    data={"geom": "LINESTRING(0 0, 1 1)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())
