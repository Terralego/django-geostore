from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient

from terracommon.terra.models import TerraUser


class AuthenticationTestCase(TestCase):
    USERNAME = 'foo@bar.com'
    USER_PASSWORD = '123456'

    def setUp(self):
        self.client = APIClient()
        self.user = TerraUser.objects.create_user(
            email=self.USERNAME,
            password=self.USER_PASSWORD
        )

    def test_authentication_jwt(self):
        """Feature with valid properties is successfully POSTed"""
        response = self.client.post(reverse('token-obtain'),
                                    {
                                        'email': self.USERNAME,
                                        'password': self.USER_PASSWORD
                                    },)

        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

        token = response.data.get('token', False)

        response = self.client.post(reverse('token-verify'),
                                    {
                                        'token': token,
                                    },)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(token, response.data.get('token'))

    def test_fail_authentication(self):
        response = self.client.post(reverse('token-obtain'),
                                    {
                                        'email': 'invalid@user.com',
                                        'password': self.USER_PASSWORD
                                    },)

        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.data)
