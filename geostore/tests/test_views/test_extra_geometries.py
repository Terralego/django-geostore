import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from geostore import GeometryTypes
from geostore.tests.factories import FeatureFactory, LayerFactory
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
                                                      'id_extra_feature': extra_feature.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response, {'id': extra_feature.pk, 'geom': {'type': 'Point', 'coordinates': [1.44, 43.6]}})

    def test_get_extra_features_do_not_exists(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )

        response = self.client.get(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'id_extra_feature': 999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_extra_features(self):
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
        response = self.client.post(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'id_extra_feature': extra_feature.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

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
            reverse('feature-extra_layer_geometry', kwargs={'layer': str(self.layer.name),
                                                            'identifier': str(feature.identifier),
                                                            'id_extra_layer': layer_extra_geom.pk}),
            {'geom': json.dumps(self.point)}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        json_response = response.json()
        extra_feature = FeatureExtraGeom.objects.first()
        self.assertEqual(json_response, {'id': extra_feature.pk, 'geom': {'type': 'Point', 'coordinates': [1.44, 43.6]}})

    def test_post_extra_layer_bad_geom(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test')
        response = self.client.post(
            reverse('feature-extra_layer_geometry', kwargs={'layer': str(self.layer.name),
                                                            'identifier': str(feature.identifier),
                                                            'id_extra_layer': layer_extra_geom.pk}),
            {'geom': "WRONG_GEOM"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        json_response = response.json()
        self.assertEqual(json_response, {'geom': ['Unable to convert to python object: '
                                                  'String input unrecognized as WKT EWKT, and HEXEWKB.']})

    def test_post_extra_layer_do_not_exists(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        response = self.client.post(
            reverse('feature-extra_layer_geometry', kwargs={'layer': str(self.layer.name),
                                                            'identifier': str(feature.identifier),
                                                            'id_extra_layer': 999}),
            {'geom': json.dumps(self.point)}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_extra_layer_not_editable(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test',
                                                         editable=False)
        response = self.client.post(
            reverse('feature-extra_layer_geometry', kwargs={'layer': str(self.layer.name),
                                                            'identifier': str(feature.identifier),
                                                            'id_extra_layer': layer_extra_geom.pk}),
            {'geom': json.dumps(self.point)}
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_extra_layer(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test')
        response = self.client.get(
            reverse('feature-extra_layer_geometry', kwargs={'layer': str(self.layer.name),
                                                            'identifier': str(feature.identifier),
                                                            'id_extra_layer': layer_extra_geom.pk}),
            {'geom': json.dumps(self.point)}
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_extra_feature(self):
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
        self.assertEqual(feature.extra_geometries.count(), 1)
        response = self.client.delete(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'id_extra_feature': extra_feature.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(feature.extra_geometries.count(), 0)

    def test_delete_extra_feature_not_editable(self):
        feature = FeatureFactory(
            layer=self.layer,
            geom=GEOSGeometry(json.dumps(self.linestring)),
            properties={'number': 1, 'text': 'bar'},
        )
        layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test',
                                                         editable=False)
        extra_feature = FeatureExtraGeom.objects.create(layer_extra_geom=layer_extra_geom, feature=feature,
                                                        geom=GEOSGeometry(json.dumps(self.point)))
        self.assertEqual(feature.extra_geometries.count(), 1)
        response = self.client.delete(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'id_extra_feature': extra_feature.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(feature.extra_geometries.count(), 1)

    def test_edit_extra_features(self):
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
        response = self.client.put(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'id_extra_feature': extra_feature.pk}),
            data={'geom': json.dumps(self.linestring)}, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        json_response = response.json()
        self.assertEqual(json_response, {'id': extra_feature.pk,
                                         'geom': {'type': 'LineString',
                                                  'coordinates': [[1.440925598144531, 43.64750394449096],
                                                                  [1.440582275390625, 43.574421623084234]]}})

    def test_edit_extra_features_bad_geom(self):
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
        response = self.client.put(
            reverse('feature-extra_geometry', kwargs={'layer': str(self.layer.name),
                                                      'identifier': str(feature.identifier),
                                                      'id_extra_feature': extra_feature.pk}),
            data={'geom': "WRONG_GEOM"}, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        json_response = response.json()
        self.assertEqual(json_response, {'geom': ['Unable to convert to python object: '
                                                  'String input unrecognized as WKT EWKT, and HEXEWKB.']})
