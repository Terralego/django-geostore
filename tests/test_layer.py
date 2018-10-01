import os
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.tokens import default_token_generator
from django.contrib.gis.geos import GEOSException
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.status import (HTTP_200_OK, HTTP_204_NO_CONTENT,
                                   HTTP_403_FORBIDDEN)

from terracommon.accounts.mixins import UserTokenGeneratorMixin
from terracommon.accounts.tests.factories import TerraUserFactory

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
        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(
            f'{shape_url}?token={token}&uidb64={uidb64}')
        self.assertEqual(HTTP_200_OK, response.status_code)

        zip = ZipFile(BytesIO(response.content), 'r')
        self.assertListEqual(
            sorted(['prj', 'cpg', 'shx', 'shp', 'dbf']),
            sorted([f.split('.')[1] for f in zip.namelist()])
            )

    def test_empty_shapefile_export(self):
        # Create en ampty layer to test its behavior
        LayerFactory()

        uidb64, token = self.get_uidb64_token_for_user()
        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(
            f'{shape_url}?token={token}&uidb64={uidb64}')
        self.assertEqual(HTTP_204_NO_CONTENT, response.status_code)

    def test_shapefile_fake_token(self):
        url = "{}?token=aaa&uidb64=zzzzz".format(
            reverse('layer-shapefile', args=[self.layer.pk, ]))

        self.assertEqual(
            self.client.get(url).status_code,
            HTTP_403_FORBIDDEN
        )

    def test_shapefile_import(self):
        layer = LayerFactory()
        shapefile_path = os.path.join(os.path.dirname(__file__),
                                      'files',
                                      'shapefile.zip')

        with ZipFile(shapefile_path, 'r') as shapezip:
            try:
                shapefile = [
                        f'/{name}'
                        for name in shapezip.namelist()
                        if name.endswith('.shp')
                    ][0]
            except IndexError:
                shapefile = None

        layer.from_shapefile(shapefile_path, shapefile)
        self.assertEqual(8, layer.features.all().count())

    def get_uidb64_token_for_user(self):
        return (urlsafe_base64_encode(force_bytes(self.user.pk)).decode(),
                default_token_generator.make_token(self.user))
