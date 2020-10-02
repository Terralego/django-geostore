from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from geostore.tests.factories import LayerFactory, FeatureFactory


class BaseRendererTestCase:
    @classmethod
    def setUpTestData(cls):
        # create a geometry undefined layer with all kind of geometry as features
        props = {"name": "test", "label": "Test"}
        cls.layer = LayerFactory()
        cls.point = FeatureFactory(layer=cls.layer,
                                   geom="POINT(0 0)", properties=props)
        cls.line = FeatureFactory(layer=cls.layer,
                                  geom="LINESTRING(0 0, 1 1)", properties=props)
        cls.polygon = FeatureFactory(
            layer=cls.layer,
            geom="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0), (0.4 0.4, 0.5 0.4, 0.5 0.5, 0.4 0.5, 0.4 0.4 ))",
            properties=props
        )
        cls.multipoint = FeatureFactory(layer=cls.layer,
                                        geom="MULTIPOINT((0 0), (1 0))", properties=props)
        cls.multilinestring = FeatureFactory(layer=cls.layer,
                                             geom="MULTILINESTRING((3 4,10 50,20 25),(-5 -8,-10 -8,-15 -4))",
                                             properties=props)
        cls.multipolygon = FeatureFactory(
            layer=cls.layer,
            geom="MULTIPOLYGON(((1 1,5 1,5 5,1 5,1 1),(2 2,2 3,3 3,3 2,2 2)),((6 3,9 2,9 4,6 3)))",
            properties=props
        )
        cls.geometrycollection = FeatureFactory(
            layer=cls.layer,
            geom="GEOMETRYCOLLECTION(POINT(4 6),LINESTRING(4 6,7 10))",
            properties=props
        )

    def test_feature_list(self):
        response = self.client.get(
            reverse('feature-list',
                    kwargs={
                        "layer": self.layer.pk,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_point(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.point.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_linestring(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.line.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_polygon(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.polygon.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_multipoint(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.multipoint.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_multilinestring(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.multilinestring.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_multipolygon(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.multipolygon.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_feature_detail_geometrycollection(self):
        response = self.client.get(
            reverse('feature-detail',
                    kwargs={
                        "layer": self.layer.pk,
                        "identifier": self.geometrycollection.identifier,
                        "format": self.format
                    })
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GPXRendererTestCase(BaseRendererTestCase, APITestCase):
    format = "gpx"

    def test_feature_list(self):
        """ Not Implemented """
        pass


class KMLRendererTestCase(BaseRendererTestCase, APITestCase):
    format = "kml"


class GeoJSONRendererTestCase(BaseRendererTestCase, APITestCase):
    format = "geojson"
