from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from terracommon.terra.tests.factories import LayerFactory, UserFactory


class SchemaValidationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

        self.no_schema_layer = LayerFactory(name="no schema", geom_type=None)
        self.valid_schema = {
            "properties": {
                "name": {
                    "type": "string"
                },
                "age": {
                    "type": "integer"
                }
            }
        }
        self.property_schema_layer = LayerFactory(
            name="tree",
            schema=self.valid_schema)

    def test_create_layer_without_valid_schema(self):
        """
        Try to create layer with valid schema
        """
        response = self.client.post(reverse('terra:layer-list'),
                                    data={})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_layer_with_valid_schema(self):
        """
        Try to create layer with valid schema
        """
        response = self.client.post(reverse('terra:layer-list'),
                                    data={"schema": self.valid_schema})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_layer_unvalid_schema(self):
        """
        Try to create layer with unvalid schema
        """
        response = self.client.post(reverse('terra:layer-list'),
                                    data={"schema": {"type": "unknown"}})
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("schema", response_json)

    def test_no_schema_properties_ok(self):
        """
        If no schema defined (or empty), all properties are accepted
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.no_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

    def test_schema_property_match_good(self):
        """
        If schema defined, allow features with properties in schema
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"name": "ok",
                                                         "age": 10}})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

    def test_schema_property_match_bad(self):
        """
        If schema defined, deny unvalid data
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.property_schema_layer.pk, ]),
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
        response = self.client.post(reverse('terra:feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}})
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("properties", response_json)
        self.assertIn("toto", response_json['properties'][0])
