from django.test import TestCase

from terra.models import zoom_update
from terra.tests.factories import LayerFactory


class ZoomUpdateTest(TestCase):
    def test_zoom_update(self):
        self.layer = LayerFactory()
        with self.assertRaises(KeyError):
            self.layer.layer_settings('tiles', 'maxzoom')

        # Call the decorator manualy on nop lambda
        self.layer.beta_lambda = lambda *args, **kargs: False
        zoom_update(self.layer.beta_lambda)(self.layer)

        self.assertEqual(
            self.layer.layer_settings('tiles', 'maxzoom') is not None,
            True)
