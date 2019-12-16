from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from geostore.tests.factories import LayerFactory, UserFactory, SchemaFactory


class SchemaValidationTest(APITestCase):
    def setUp(self):
        self.user = UserFactory(permissions=['geostore.can_manage_layers', ])
        self.client.force_authenticate(user=self.user)
        self.no_schema_layer = LayerFactory(name="no schema", geom_type=None)
        self.property_schema_layer = LayerFactory(name="tree")
        SchemaFactory.create(slug="name", title="Name", layer=self.property_schema_layer)
        SchemaFactory.create(slug="age", title="Age", prop_type="integer", layer=self.property_schema_layer)

    def test_no_schema_properties_ok(self):
        """
        If no schema defined (or empty), all properties are accepted
        """
        response = self.client.post(reverse('feature-list', args=[self.no_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

    def test_schema_property_match_good(self):
        """
        If schema defined, allow features with properties in schema
        """
        response = self.client.post(reverse('feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"name": "ok",
                                                         "age": 10}})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

    def test_schema_property_match_bad(self):
        """
        If schema defined, deny unvalid data
        """
        response = self.client.post(reverse('feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"name": 20,
                                                         "age": "wrong data"}})
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("properties", response_json)
        self.assertIn("wrong data", response_json['properties'][0])

    def test_schema_property_doesnt_match(self):
        """
        If schema defined, deny properties not in schema
        """
        response = self.client.post(reverse('feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("properties", response_json)
        self.assertIn("toto", response_json['properties'][0])
