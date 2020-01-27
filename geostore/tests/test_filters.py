from geostore.models import Feature
from rest_framework import status
from rest_framework.reverse import reverse

from geostore.tests.factories import UserFactory, LayerFactory, SchemaFactory
from rest_framework.test import APITestCase


class LayerFeatureListOrderingTestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory(permissions=['geostore.can_manage_layers', ])
        self.client.force_authenticate(user=self.user)

        self.property_schema_layer = LayerFactory(
            name="tree",
        )
        SchemaFactory.create(slug="name", title="Name", layer=self.property_schema_layer)
        SchemaFactory.create(slug="age", title="Age", prop_type="int", layer=self.property_schema_layer)
        Feature.objects.bulk_create([
            Feature(layer=self.property_schema_layer,
                    properties={'name': '1',
                                'age': 1},
                    geom='POINT(0 0)'),
            Feature(layer=self.property_schema_layer,
                    properties={'name': '2',
                                'age': 2},
                    geom='POINT(0 0)'),
            Feature(layer=self.property_schema_layer,
                    properties={'name': '10',
                                'age': 10},
                    geom='POINT(0 0)')
        ])

    def test_filtering_order_asc_integer(self):
        """ Test order by integer asc. Should order in 1,2,10 """
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'ordering': 'properties__age'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(self.property_schema_layer.features.count(),
                         len(data))
        ages = [x['properties']['age'] for x in data]
        self.assertEqual(ages, [1, 2, 10])

    def test_filtering_order_desc_integer(self):
        """ Test order by integer desc. Should order in 10,2,1 """
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'ordering': '-properties__age'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(self.property_schema_layer.features.count(),
                         len(data))
        ages = [x['properties']['age'] for x in data]
        self.assertEqual(ages, [10, 2, 1])

    def test_filtering_order_asc_string(self):
        """ Test order by string asc. Should order in 1,10,2 """
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'ordering': 'properties__name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(self.property_schema_layer.features.count(),
                         len(data))
        names = [x['properties']['name'] for x in data]
        self.assertEqual(names, ['1', '10', '2'])

    def test_filtering_order_desc_string(self):
        """ Test order by string desc. Should order in 2,10,1 """
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'ordering': '-properties__name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(self.property_schema_layer.features.count(),
                         len(data))
        names = [x['properties']['name'] for x in data]
        self.assertEqual(names, ['2', '10', '1'])


class LayerFeatureListSearchTestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory(permissions=['geostore.can_manage_layers', ])
        self.client.force_authenticate(user=self.user)
        self.property_schema_layer = LayerFactory(
            name="tree",
        )
        SchemaFactory.create(slug="name", title="Name", layer=self.property_schema_layer)
        SchemaFactory.create(slug="age", title="Age", prop_type="int", layer=self.property_schema_layer)
        Feature.objects.bulk_create([
            Feature(layer=self.property_schema_layer,
                    properties={'name': 'John',
                                'age': 1},
                    geom='POINT(0 0)'),
            Feature(layer=self.property_schema_layer,
                    properties={'name': 'Jack',
                                'age': 2},
                    geom='POINT(0 0)'),
            Feature(layer=self.property_schema_layer,
                    properties={'name': 'Jeremy',
                                'age': 10},
                    geom='POINT(0 0)')
        ])

    def test_searching_ok(self):
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'search': 'Jack'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(1,
                         len(data))

    def test_searching_ko(self):
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'search': 'Jeremya'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(0,
                         len(data))

    def test_searching_j(self):
        response = self.client.get(reverse('feature-list',
                                           args=(self.property_schema_layer.pk, )),
                                   data={'search': 'J'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(3,
                         len(data))
