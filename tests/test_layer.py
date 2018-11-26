import json
import os
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import Permission
from django.contrib.auth.tokens import default_token_generator
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.status import (HTTP_200_OK, HTTP_204_NO_CONTENT,
                                   HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN)
from rest_framework.test import APIClient

from terracommon.accounts.mixins import UserTokenGeneratorMixin
from terracommon.accounts.tests.factories import TerraUserFactory
from terracommon.terra.models import zoom_update

from .factories import FeatureFactory, LayerFactory


class LayerTestCase(TestCase, UserTokenGeneratorMixin):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = TerraUserFactory()
        self.client.force_login(self.user)

    def test_import_geojson(self):
        with_projection = """{"type": "FeatureCollection", "crs":
                             { "type": "name", "properties": { "name":
                             "urn:ogc:def:crs:OGC:1.3:CRS84" } },
                             "features": []}"""
        self.layer.from_geojson(with_projection, "01-01", "01-01")

        without_projection = """{"type": "FeatureCollection",
                                "features": []}"""
        self.layer.from_geojson(without_projection, "01-01", "01-01")

        with_bad_projection = """{"type": "FeatureCollection", "crs":
                                 { "type": "name", "properties": { "name":
                                 "BADPROJECTION" } }, "features": []}"""
        with self.assertRaises(GEOSException):
            self.layer.from_geojson(with_bad_projection, "01-01", "01-01")

    def test_shapefile_export(self):
        # Create at least one feature in the layer, so it's not empty
        FeatureFactory(layer=self.layer)

        uidb64, token = self.get_uidb64_token_for_user()
        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(
            f'{shape_url}?token={token}&uidb64={uidb64}')
        self.assertEqual(HTTP_200_OK, response.status_code)

        zip = ZipFile(BytesIO(response.content), 'r')
        self.assertListEqual(
            sorted(['prj', 'cpg', 'shx', 'shp', 'dbf']),
            sorted([f.split('.')[1] for f in zip.namelist()])
            )

    def test_shapefile_same_import_export(self):
        FeatureFactory(layer=self.layer, properties={
            'key1': [{
                'key3': 'hello world',
            }]
        })

        uidb64, token = self.get_uidb64_token_for_user()
        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(
            f'{shape_url}?token={token}&uidb64={uidb64}')
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

        uidb64, token = self.get_uidb64_token_for_user()
        shape_url = reverse('terra:layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(
            f'{shape_url}?token={token}&uidb64={uidb64}')
        self.assertEqual(HTTP_204_NO_CONTENT, response.status_code)

    def test_shapefile_fake_token(self):
        url = "{}?token=aaa&uidb64=zzzzz".format(
            reverse('terra:layer-shapefile', args=[self.layer.pk, ]))

        self.assertEqual(
            self.client.get(url).status_code,
            HTTP_403_FORBIDDEN
        )

    def test_no_shapefile_import(self):
        layer = LayerFactory()

        response = self.client.post(
            reverse('terra:layer-shapefile', args=[layer.pk, ]),)

        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_shapefile_import(self):
        layer = LayerFactory()
        shapefile_path = os.path.join(os.path.dirname(__file__),
                                      'files',
                                      'shapefile-WGS84.zip')

        with open(shapefile_path, 'rb') as shapefile:
            layer.from_shapefile(shapefile)

        self.assertEqual(8, layer.features.all().count())

    def test_shapefile_import_view(self):
        layer = LayerFactory()

        shapefile_path = os.path.join(os.path.dirname(__file__),
                                      'files',
                                      'shapefile-WGS84.zip')

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
        shapefile = SimpleUploadedFile('shapefile-WGS84.zip',
                                       b'bad bad data')

        response = self.client.post(
            reverse('terra:layer-shapefile', args=[self.layer.pk, ]),
            {'shapefile': shapefile, }
            )
        self.assertEqual(HTTP_400_BAD_REQUEST, response.status_code)

    def test_to_geojson(self):
        # Create at least one feature in the layer, so it's not empty
        FeatureFactory(layer=self.layer)

        uidb64, token = self.get_uidb64_token_for_user()
        geojson_url = reverse('terra:layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(
            f'{geojson_url}?token={token}&uidb64={uidb64}')

        self.assertEqual(200, response.status_code)

        response = response.json()
        self.assertEqual('FeatureCollection', response.get('type'))
        self.assertEqual(self.layer.features.all().count(),
                         len(response.get('features')))

    def get_uidb64_token_for_user(self):
        return (urlsafe_base64_encode(force_bytes(self.user.pk)).decode(),
                default_token_generator.make_token(self.user))


class TestLayerFeaturesUpdate(TestCase):
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
        self.user = TerraUserFactory()
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

    def test_layer_settings(self):
        with self.assertRaises(KeyError):
            self.layer.layer_settings('foo', 'bar', '666')

        with self.assertRaises(KeyError):
            self.layer.layer_settings('tiles', 'minzoom')

        self.assertEqual(
            self.layer.layer_settings_with_default('tiles', 'minzoom'),
            0
        )

    def test_set_layer_settings(self):
        with self.assertRaises(KeyError):
            self.layer.layer_settings('foo', 'bar')

        self.layer.set_layer_settings('foo', 'bar', 123)

        self.assertEqual(
            self.layer.layer_settings('foo', 'bar'),
            123
        )

        self.assertEqual(
            self.layer.layer_settings_with_default('foo', 'bar'),
            123
        )

    def test_zoom_update(self):
        with self.assertRaises(KeyError):
            self.layer.layer_settings('tiles', 'maxzoom')

        # Call the decorator manualy on nop lambda
        self.layer.beta_lambda = lambda *args, **kargs: False
        zoom_update(self.layer.beta_lambda)(self.layer)

        self.assertEqual(
            self.layer.layer_settings('tiles', 'maxzoom') is not None,
            True)
