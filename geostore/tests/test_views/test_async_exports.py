import json
from datetime import datetime
from tempfile import TemporaryDirectory
from unittest import mock, skipIf
from xml.etree import ElementTree as ET

from django.contrib.gis.geos import GEOSGeometry
from django.core import mail
from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from geostore import settings as app_settings
from geostore.tests.factories import FeatureFactory, LayerFactory, SuperUserFactory


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
@skipIf(not app_settings.GEOSTORE_EXPORT_CELERY_ASYNC, 'Test with export async only')
class LayerKMLExportAsyncTestCase(APITestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = SuperUserFactory(email="foo@foo.foo")
        self.client.force_authenticate(self.user)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_kml_export_no_mail(self, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect(async_func, args):
            async_func(*args)
        mock_async_func.side_effect = side_effect
        FeatureFactory(layer=self.layer)
        user = SuperUserFactory(email='')
        self.client.force_authenticate(user)
        kml_url = reverse('layer-kml', args=[self.layer.pk, ])
        response = self.client.get(kml_url)
        self.assertEqual(status.HTTP_406_NOT_ACCEPTABLE, response.status_code)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_kml_export_with_mail_empty_data(self, mock_async):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        shape_url = reverse('layer-kml', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = r'Your file is ready'
        self.assertNotRegex(mail.outbox[0].body, path_export)

    @mock.patch('geostore.views.execute_async_func')
    @mock.patch('geostore.import_export.helpers.now')
    def test_async_kml_export_with_mail(self, mock_time, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect_async(async_func, args):
            async_func(*args)

        def side_effect_now():
            return datetime(2020, 3, 16, 1, 1, 1)

        mock_async_func.side_effect = side_effect_async
        mock_time.side_effect = side_effect_now
        FeatureFactory(layer=self.layer)

        kml_url = reverse('layer-kml', args=[self.layer.pk, ])
        response = self.client.get(kml_url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = 'exports/users/{}/{}_1584320461.kml'.format(self.user.id, self.layer.name)
        self.assertIn(path_export, mail.outbox[0].body)
        with default_storage.open(path_export) as fp:
            kml = fp.read().decode('utf-8')
            xml = ET.fromstring(kml)
            self.assertEqual(list(xml[0][0])[-1][0].text, '2.4609375,45.583289756006316,0.0')


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
@skipIf(not app_settings.GEOSTORE_EXPORT_CELERY_ASYNC, 'Test with export async only')
class LayerGeojsonExportAsyncTestCase(APITestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = SuperUserFactory(email="foo@foo.foo")
        self.client.force_authenticate(self.user)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_geojson_export_no_mail(self, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect(async_func, args):
            async_func(*args)
        mock_async_func.side_effect = side_effect
        FeatureFactory(layer=self.layer)
        user = SuperUserFactory(email='')
        self.client.force_authenticate(user)
        geojson_url = reverse('layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(geojson_url)
        self.assertEqual(status.HTTP_406_NOT_ACCEPTABLE, response.status_code)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_geojson_export_with_mail_empty_data(self, mock_async):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        shape_url = reverse('layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = r'Your file is ready'
        self.assertNotRegex(mail.outbox[0].body, path_export)

    @mock.patch('geostore.views.execute_async_func')
    @mock.patch('geostore.import_export.helpers.now')
    def test_async_geojson_export_with_mail(self, mock_time, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect_async(async_func, args):
            async_func(*args)

        def side_effect_now():
            return datetime(2020, 3, 16, 1, 1, 1)

        mock_async_func.side_effect = side_effect_async
        mock_time.side_effect = side_effect_now
        FeatureFactory(layer=self.layer)

        geojson_url = reverse('layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(geojson_url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = r'exports/users/{}/{}_1584320461.geojson'.format(self.user.id, self.layer.name)
        self.assertRegex(mail.outbox[0].body, path_export)
        with default_storage.open(path_export) as fp:
            geojson = json.loads(fp.read())
        feature = geojson['features'][0]['geometry']
        feature_geom = GEOSGeometry(json.dumps(feature))
        self.assertAlmostEquals(feature_geom.x, 2.4609375)
        self.assertAlmostEquals(feature_geom.y, 45.58328975600632)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
@skipIf(not app_settings.GEOSTORE_EXPORT_CELERY_ASYNC, 'Test with export async only')
class LayerShapefileExportAsyncTestCase(APITestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = SuperUserFactory(email="foo@foo.foo")
        self.client.force_authenticate(self.user)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_shapefile_export_no_mail(self, mock_async):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        FeatureFactory(layer=self.layer)
        user = SuperUserFactory(email='')
        self.client.force_authenticate(user)
        shape_url = reverse('layer-shapefile_async', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(status.HTTP_406_NOT_ACCEPTABLE, response.status_code)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_shapefile_export_with_mail_empty_data(self, mock_async):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        shape_url = reverse('layer-shapefile_async', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = r'Your file is ready'
        self.assertNotRegex(mail.outbox[0].body, path_export)

    @mock.patch('geostore.views.execute_async_func')
    @mock.patch('geostore.import_export.helpers.now')
    def test_async_shapefile_export_with_mail(self, mock_time, mock_async_func):
        def side_effect_async(async_func, args):
            async_func(*args)

        def side_effect_now():
            return datetime(2020, 3, 16, 1, 1, 1)

        mock_async_func.side_effect = side_effect_async
        mock_time.side_effect = side_effect_now
        FeatureFactory(layer=self.layer)
        shape_url = reverse('layer-shapefile_async', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(status.HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = r'exports/users/{}/{}_1584320461.zip'.format(self.user.id, self.layer.name)
        self.assertRegex(mail.outbox[0].body, path_export)
