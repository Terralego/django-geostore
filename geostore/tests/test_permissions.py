from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from geostore.models import Layer
from geostore.permissions import (
    FeaturePermission,
    LayerImportExportPermission,
    LayerPermission,
)
from geostore.tests.factories import SuperUserFactory, UserFactory

UserModel = get_user_model()


class PermissionsTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory(permissions=[])
        self.group = Group.objects.create(name="testgroup")
        self.layer = Layer.objects.create(name="testlayer")

    def test_layer_permission_has_permission(self):
        permission = LayerPermission()
        req_safe = MagicMock(method="GET", user=self.user)
        self.assertTrue(permission.has_permission(req_safe, None))

        req_unsafe = MagicMock(method="POST", user=self.user)
        self.assertFalse(permission.has_permission(req_unsafe, None))

        user_with_perm = UserFactory(permissions=["geostore.can_manage_layers"])
        req_unsafe_perm = MagicMock(method="POST", user=user_with_perm)
        self.assertTrue(permission.has_permission(req_unsafe_perm, None))

    def test_layer_permission_has_object_permission(self):
        permission = LayerPermission()
        superuser = SuperUserFactory()
        req_su = MagicMock(user=superuser)
        self.assertTrue(permission.has_object_permission(req_su, None, self.layer))

        # Layer without authorized groups: safe method returns True, unsafe returns False without perm
        req_get = MagicMock(method="GET", user=self.user)
        self.assertTrue(permission.has_object_permission(req_get, None, self.layer))
        req_post = MagicMock(method="POST", user=self.user)
        self.assertFalse(permission.has_object_permission(req_post, None, self.layer))

        # Layer with authorized groups
        self.layer.authorized_groups.add(self.group)

        # Unsafe method without can_manage_layers
        self.assertFalse(permission.has_object_permission(req_post, None, self.layer))

        # Safe method without being in group
        self.assertFalse(permission.has_object_permission(req_get, None, self.layer))

        # User in group has object permission for safe method
        self.user.groups.add(self.group)
        self.user = UserModel.objects.get(pk=self.user.pk)
        req_get.user = self.user
        self.assertTrue(permission.has_object_permission(req_get, None, self.layer))

        # Unsafe method with can_manage_layers and user in group
        user_with_perm = UserFactory(permissions=["geostore.can_manage_layers"])
        user_with_perm.groups.add(self.group)
        user_with_perm = UserModel.objects.get(pk=user_with_perm.pk)
        req_post.user = user_with_perm
        self.assertTrue(permission.has_object_permission(req_post, None, self.layer))

    def test_layer_import_export_permission(self):
        permission = LayerImportExportPermission()
        req_post = MagicMock(method="POST", user=self.user)
        self.assertFalse(permission.has_permission(req_post, None))
        user_import = UserFactory(permissions=["geostore.can_import_layers"])
        req_post.user = user_import
        self.assertTrue(permission.has_permission(req_post, None))

        req_get = MagicMock(method="GET", user=self.user)
        self.assertFalse(permission.has_permission(req_get, None))
        user_export = UserFactory(permissions=["geostore.can_export_layers"])
        req_get.user = user_export
        self.assertTrue(permission.has_permission(req_get, None))

    def test_feature_permission(self):
        perm = FeaturePermission()
        self.assertIsInstance(perm, LayerPermission)
