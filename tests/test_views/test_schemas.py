from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from terracommon.accounts.tests.factories import TerraUserFactory
from terracommon.terra.tests.factories import LayerFactory


class SchemaValidationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = TerraUserFactory()
        self.client.force_authenticate(user=self.user)

        self.no_schema_layer = LayerFactory(name="no schema")
        self.property_schema_layer = LayerFactory(
            name="tree",
            schema={
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "age": {
                        "type": "integer"
                    }
                }
            })

    def test_no_schema_properties_ok(self):
        """
        If no schema defined (or empty), all properties are accepted
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.no_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

    def test_schema_property_match_good(self):
        """
        If schema defined, allow features with properties in schema
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"name": "ok",
                                                         "age": 10}},
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

    def test_schema_property_match_bad(self):
        """
        If schema defined, deny unvalid data
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"name": 20,
                                                         "age": "wrong data"}},
                                    format='json')
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("properties", response_json)
        self.assertIn("age", response_json['properties'])

    def test_schema_property_doesnt_match(self):
        """
        If schema defined, deny properties not in schema
        """
        response = self.client.post(reverse('terra:feature-list', args=[self.property_schema_layer.pk, ]),
                                    data={"geom": "POINT(0 0)",
                                          "properties": {"toto": "ok"}},
                                    format='json')
        response_json = response.json()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("properties", response_json)
        self.assertIn("unexpected", response_json['properties'])
