from django.test import TestCase
from django.utils.text import slugify

from geostore import GeometryTypes
from geostore.models import LayerExtraGeom, Feature
from geostore.tests.factories import LayerWithSchemaFactory


class LayerExtraGeomModelTestCase(TestCase):
    def setUp(self):
        self.layer_schema = LayerWithSchemaFactory()
        self.extra_layer = LayerExtraGeom.objects.create(layer=self.layer_schema,
                                                         geom_type=GeometryTypes.Point,
                                                         title='Test')

    def test_str(self):
        self.assertEqual(str(self.extra_layer),
                         f'{self.extra_layer.title} ({str(self.layer_schema)})')

    def test_name(self):
        self.assertEqual(self.extra_layer.name,
                         f'{slugify(self.extra_layer.layer.name)}-{self.extra_layer.slug}')


class FeatureTestCase(TestCase):
    def setUp(self):
        self.layer_schema = LayerWithSchemaFactory()

    def test_clean(self):
        feature = Feature.objects.create(layer=self.layer_schema,
                                         geom='POINT(0 0)',
                                         properties={
                                             'name': 'toto'
                                         })
        feature.clean()
        self.assertIsNotNone(feature.pk)
