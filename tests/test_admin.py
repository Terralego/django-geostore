from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from terracommon.terra.models import Layer
from terracommon.terra.tests.factories import LayerFactory


class MockRequest:
    pass


class MockSuperUser:
    def has_perm(self, perm):
        return True


request = MockRequest()
request.user = MockSuperUser()


class ModelAdminLayerTest(TestCase):

    def setUp(self):
        self.layer = LayerFactory()
        self.site = AdminSite()

    def test_modeladmin_str(self):
        ma_layer = ModelAdmin(Layer, self.site)
        self.assertEqual(str(ma_layer), 'terra.ModelAdmin')

    def test_default_fields(self):
        ma = ModelAdmin(Layer, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'group', 'schema', 'settings'])
        self.assertEqual(list(ma.get_fields(request)), ['name', 'group', 'schema', 'settings'])
        self.assertEqual(list(ma.get_fields(request, self.layer)), ['name', 'group', 'schema', 'settings'])
        self.assertIsNone(ma.get_exclude(request, self.layer))
