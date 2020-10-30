import json
from tempfile import TemporaryDirectory
from unittest import mock, skipIf
from xml.etree import ElementTree as ET

from django.contrib.auth.models import Permission
from django.contrib.gis.geos import GEOSGeometry
from django.core import mail
from django.core.files.storage import default_storage
from django.test import override_settings, TestCase
from django.urls import reverse
from rest_framework.status import HTTP_202_ACCEPTED

from geostore import settings as app_settings
from geostore.tests.factories import (FeatureFactory, LayerFactory, SuperUserFactory,
                                      UserFactory)


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
@skipIf(not app_settings.GEOSTORE_EXPORT_CELERY_ASYNC, 'Test with export async only')
class LayerKMLExportAsyncTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = SuperUserFactory()
        self.client.force_login(self.user)

    @mock.patch('geostore.views.execute_async_func')
    def test_kml_export_no_mail(self, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect(async_func, args):
            async_func(*args)
        mock_async_func.side_effect = side_effect
        FeatureFactory(layer=self.layer)

        kml_url = reverse('layer-kml', args=[self.layer.pk, ])
        response = self.client.get(kml_url)
        self.assertEqual(HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('geostore.views.execute_async_func')
    def test_kml_export_with_mail(self, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect(async_func, args):
            async_func(*args)

        mock_async_func.side_effect = side_effect
        self.user = SuperUserFactory(email="foo@foo.foo")
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        self.client.force_login(self.user)
        FeatureFactory(layer=self.layer)

        kml_url = reverse('layer-kml', args=[self.layer.pk, ])
        response = self.client.get(kml_url)
        self.assertEqual(HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = 'exports/users/{}/{}.kml'.format(self.user.id, self.layer.name)
        self.assertIn(path_export, mail.outbox[0].body)
        with default_storage.open(path_export) as fp:
            kml = fp.read().decode('utf-8')
            xml = ET.fromstring(kml)
            self.assertEqual(list(xml[0][0])[-1][0].text, '2.4609375,45.583289756006316,0.0')


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
@skipIf(not app_settings.GEOSTORE_EXPORT_CELERY_ASYNC, 'Test with export async only')
class LayerGeojsonExportAsyncTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    @mock.patch('geostore.views.execute_async_func')
    def test_geojson_export_no_mail(self, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect(async_func, args):
            async_func(*args)
        mock_async_func.side_effect = side_effect
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        FeatureFactory(layer=self.layer)

        geojson_url = reverse('layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(geojson_url)
        self.assertEqual(HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('geostore.views.execute_async_func')
    def test_geojson_export_with_mail(self, mock_async_func):
        # Create at least one feature in the layer, so it's not empty
        def side_effect(async_func, args):
            async_func(*args)

        mock_async_func.side_effect = side_effect
        self.user = UserFactory(email="foo@foo.foo")
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        self.client.force_login(self.user)
        FeatureFactory(layer=self.layer)

        geojson_url = reverse('layer-geojson', args=[self.layer.pk, ])
        response = self.client.get(geojson_url)
        self.assertEqual(HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
        path_export = 'exports/users/{}/{}.geojson'.format(self.user.id, self.layer.name)
        self.assertIn(path_export, mail.outbox[0].body)
        with default_storage.open(path_export) as fp:
            geojson = json.loads(fp.read())
        feature = geojson['features'][0]['geometry']
        feature_geom = GEOSGeometry(json.dumps(feature)).ewkt
        self.assertEqual(feature_geom, 'SRID=4326;POINT (2.4609375 45.58328975600632)')


@override_settings(MEDIA_ROOT=TemporaryDirectory().name)
class LayerShapefileExportAsyncTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_shapefile_export_no_mail(self, mock_async):
        def side_effect(async_func, args):
            async_func(*args)
        mock_async.side_effect = side_effect
        FeatureFactory(layer=self.layer)
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch('geostore.views.execute_async_func')
    def test_async_shapefile_export_with_mail(self, mock_async):
        def side_effect(async_func, args):
            async_func(*args)

        mock_async.side_effect = side_effect
        FeatureFactory(layer=self.layer)
        self.user = UserFactory(email="foo@foo.foo")
        self.user.user_permissions.add(Permission.objects.get(codename='can_export_layers'))
        self.client.force_login(self.user)
        shape_url = reverse('layer-shapefile', args=[self.layer.pk, ])
        response = self.client.get(shape_url)
        self.assertEqual(HTTP_202_ACCEPTED, response.status_code)
        self.assertEqual(len(mail.outbox), 1)
