from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from terracommon.accounts.tests.factories import TerraUserFactory


class SettingsViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = TerraUserFactory()

        self.client.force_authenticate(user=self.user)

    def test_view(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(200, response.status_code)
        self.assertListEqual(
            ['states', ],
            list(response.json())
            )
