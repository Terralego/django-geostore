from unittest import skipIf

from rest_framework import status
from rest_framework.test import APITestCase
from geostore import settings as app_settings
from geostore.tests.factories import LayerFactory


class CustomSerializerTestCase(APITestCase):
    @skipIf(app_settings.GEOSTORE_LAYER_VIEWSSET != 'geostore.views.LayerViewSet',
            'test only with custom settings')
    def test_extended_action_is_present(self):
        response = self.client.get('layer-extended')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @skipIf(app_settings.GEOSTORE_LAYER_SERIALIZER != 'geostore.serializers.LayerSerializer',
            'test only with custom settings')
    def test_extended_serializer_is_used(self):
        self.layer = LayerFactory()
        response = self.client.get('layer-detail', args=(self.layer.pk, ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['extended'], True)
