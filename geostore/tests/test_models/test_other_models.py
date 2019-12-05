from django.test import TestCase

from geostore import GeometryTypes
from geostore.models import LayerExtraGeom
from geostore.tests.factories import LayerSchemaFactory


class LayerExtraGeomModelTestCase(TestCase):
    def setUp(self):
        self.layer_schema = LayerSchemaFactory()
        self.extra_layer = LayerExtraGeom.objects.create(layer=self.layer_schema,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test')

    def test_str(self):
        self.assertEqual(str(self.extra_layer),
                         f'{self.extra_layer.title} ({str(self.layer_schema)})')
