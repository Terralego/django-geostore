from unittest import mock

from django.test import TestCase
from geostore import GeometryTypes
from geostore.models import LayerRelation
from geostore.tasks import (
    feature_update_relations_destinations,
    layer_relations_set_destinations,
)
from geostore.tests.factories import LayerSchemaFactory, FeatureFactory


class LayerRelationTestCase(TestCase):
    def setUp(self) -> None:
        self.layer_trek = LayerSchemaFactory(geom_type=GeometryTypes.LineString)
        self.layer_city = LayerSchemaFactory(geom_type=GeometryTypes.Polygon)
        self.trek = FeatureFactory(layer=self.layer_trek, geom='LINESTRING(0 0, 1 1, 2 2, 3 3)')
        self.city_cover = FeatureFactory(layer=self.layer_city, geom='POLYGON((0 0, 0 3, 3 3, 3 0, 0 0))')
        self.city_uncover = FeatureFactory(layer=self.layer_city, geom='POLYGON((4 4, 4 7, 7 7, 7 4, 4 4))')

    def test_str(self):
        intersect_relation = LayerRelation.objects.create(
            relation_type='intersects',
            origin=self.layer_trek,
            destination=self.layer_city,
        )
        self.assertEqual(str(intersect_relation), intersect_relation.name)

    def test_sync_relations_intersects(self):
        intersect_relation = LayerRelation.objects.create(
            relation_type='intersects',
            origin=self.layer_trek,
            destination=self.layer_city,
        )
        # city cover should be present after sync
        self.trek.sync_relations(intersect_relation.pk)
        self.assertListEqual(list(self.trek.relations_as_origin.filter(relation=intersect_relation)
                                  .values_list('destination__pk', flat=True)),
                             [self.city_cover.pk])
        # city cover should not be present after deletion
        intersect_relation.delete()
        self.assertListEqual(list(self.trek.relations_as_origin.all()
                                  .values_list('destination__pk', flat=True)),
                             [])

    def test_sync_relations_distance(self):
        distance_relation = LayerRelation.objects.create(
            relation_type='distance',
            origin=self.layer_trek,
            destination=self.layer_city,
            settings={'distance': 1000}
        )
        # city cover should be present after sync
        self.trek.sync_relations(distance_relation.pk)
        self.assertListEqual(list(self.trek.relations_as_origin.filter(relation=distance_relation)
                                  .values_list('destination__pk', flat=True)),
                             [self.city_cover.pk])
        # city cover should not be present after deletion
        distance_relation.delete()
        self.assertListEqual(list(self.trek.relations_as_origin.all()
                                  .values_list('destination__pk', flat=True)),
                             [])

    def test_bad_relation(self):
        bad_relation = LayerRelation.objects.create(
            relation_type='distance',
            origin=self.layer_city,
            destination=self.layer_trek,
            settings={'distance': 1000}
        )
        self.city_cover.sync_relations(bad_relation.pk)
        self.assertListEqual(list(self.trek.get_computed_relation_qs(relation=bad_relation)
                                  .values_list('pk', flat=True)),
                             [])

    def test_relation_property(self):
        self.assertEqual(self.trek.relations, {})

    @mock.patch('geostore.models.django_version', (3, 1))
    def test_sync_relations_distance_django_lt_32(self):
        distance_relation = LayerRelation.objects.create(
            relation_type='distance',
            origin=self.layer_trek,
            destination=self.layer_city,
            settings={'distance': 1000}
        )
        self.trek.sync_relations(distance_relation.pk)
        self.assertListEqual(list(self.trek.relations_as_origin.filter(relation=distance_relation)
                                  .values_list('destination__pk', flat=True)),
                             [self.city_cover.pk])

    def test_tasks_update_relations(self):
        intersect_relation = LayerRelation.objects.create(
            relation_type='intersects',
            origin=self.layer_trek,
            destination=self.layer_city,
        )
        res1 = feature_update_relations_destinations(self.trek.pk, intersect_relation.pk)
        self.assertTrue(res1)
        with mock.patch('geostore.tasks.feature_update_relations_destinations.delay') as mock_delay:
            res2 = layer_relations_set_destinations(intersect_relation.pk)
            self.assertTrue(res2)
            mock_delay.assert_called_with(self.trek.pk, intersect_relation.pk)
