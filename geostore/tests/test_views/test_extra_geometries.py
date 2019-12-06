import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from geostore import GeometryTypes
from geostore.tests.factories import (FeatureFactory, LayerFactory, LayerSchemaFactory)
from geostore.models import LayerExtraGeom, FeatureExtraGeom


class ExtraGeometriesListViewTest(TestCase):
    linestring = {
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
    point = {
        "type": "Point",
        "coordinates": [
            1.44,
            43.6
        ]
    }
    geojson_to_render = {'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:4326'}},
                         'features': [{'type': 'Feature', 'properties': {},
                                       'geometry': {'type': 'Point', 'coordinates': [1.44, 43.6]}}]}

    def setUp(self):
        self.layer = LayerFactory.create()

    def test_get_extra_features(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test')
        extra_feature = FeatureExtraGeom.objects.create(layer_extra_geom=layer_extra_geom, feature=feature,
                                                        geom=GEOSGeometry(json.dumps(self.point)))
        feature.extra_geometries.add(extra_feature)
        response = self.client.get(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'extrageometry': extra_feature.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response, self.geojson_to_render)

    def test_get_extra_features_do_not_exists(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        response = self.client.get(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'extrageometry': 999})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_post_extra_layer(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test')
        response = self.client.post(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'extrageometry': layer_extra_geom.pk}),
            {'geom': json.dumps(self.point)}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response, self.geojson_to_render)

    def test_post_extra_layer_do_not_exists(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        response = self.client.post(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'extrageometry': 999}),
            {'geom': json.dumps(self.point)}
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
