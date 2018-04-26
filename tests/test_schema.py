import json

from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient, force_authenticate

from terracommon.terra.models import Layer, Feature, TerraUser


class SchemaValidationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = TerraUser.objects.create_user(
            email='foo@bar.com',
            password='123456'
        )
        self.client.force_authenticate(user=self.user)

        self.layer = Layer.objects.create(
            name="tree",
            schema={
                "name": {
                    "type": "string"
                },
                "age": {
                    "type": "integer"
                }
            })

    def test_feature_with_valid_properties_is_posted(self):
        """Feature with valid properties is successfully POSTed"""
        response = self.client.post(reverse('feature-list', args=[self.layer.id, ]),
                                    {
                                            "geom": "POINT(0 0)",
                                            "layer": self.layer.id,
                                            "name": "valid tree",
                                            "age": 10
                                    },
                                    format='json',
                                    )

        features = Feature.objects.all()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].properties['name'], 'valid tree')

    def test_feature_with_missing_property_type_is_not_posted(self):
        """Feature with missing property type is not successfully POSTed"""
        response = self.client.post(reverse('feature-list', args=[self.layer.id, ]),
                                    {
                                        "geom": "POINT(0 0)",
                                        "layer": self.layer.id,
                                        "name": "invalid tree"
                                    },
                                    format='json'
                                    )

        self.assertEqual(response.status_code, 400)
