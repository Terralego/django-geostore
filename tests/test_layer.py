from io import BytesIO
from zipfile import ZipFile

from django.contrib.gis.geos import GEOSException
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from terracommon.accounts.tests.factories import TerraUserFactory

from .factories import FeatureFactory, LayerFactory


class LayerTestCase(TestCase):
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
        FeatureFactory(layer=self.layer)

        response = self.client.get(reverse('layer-shapefile',
                                           args=[self.layer.pk]))
        self.assertEqual(HTTP_200_OK, response.status_code)

        zip = ZipFile(BytesIO(response.content), 'r')
        self.assertListEqual(
            ['prj', 'cpg', 'shx', 'shp', 'dbf'],
            [f.split('.')[1] for f in zip.namelist()]
            )

    def test_empty_shapefile_export(self):
        empty_layer = LayerFactory()

        response = self.client.get(reverse('layer-shapefile',
                                           args=[empty_layer.pk]))
        self.assertEqual(HTTP_204_NO_CONTENT, response.status_code)
