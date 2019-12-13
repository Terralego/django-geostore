from django.test import TestCase
from geostore import GeometryTypes
from geostore.models import LayerRelation

from geostore.tests.factories import LayerSchemaFactory, FeatureFactory


class TestLayerRelationTestCase(TestCase):
    def setUp(self) -> None:
        self.layer_trek = LayerSchemaFactory(geom_type=GeometryTypes.LineString)
        self.layer_city = LayerSchemaFactory(geom_type=GeometryTypes.Polygon)
        self.intersect_relation = LayerRelation.objects.create(
            relation_type='intersects',
            origin=self.layer_trek,
            destination=self.layer_city,
        )
        self.trek = FeatureFactory(layer=self.layer_trek, geom='LINESTRING(0 0, 1 1, 2 2, 3 3)')
        self.city_cover = FeatureFactory(layer=self.layer_city, geom='POLYGON((0 0, 0 3, 3 3, 3 0, 0 0))')
        self.city_uncover = FeatureFactory(layer=self.layer_city, geom='POLYGON((4 4, 4 7, 7 7, 7 4, 4 4))')

    def test_sync_relations_original(self):
        self.trek.sync_relations()
        self.assertListEqual(list(self.trek.relations_as_origin.values_list('destination__pk', flat=True)),
                             [self.city_cover.pk])
