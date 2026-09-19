from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class IdentityTests(APITestCase):
    def test_create_user_with_email(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="analyst@example.com",
            password="StrongPass123",
        )
        self.assertEqual(user.email, "analyst@example.com")
        self.assertTrue(user.check_password("StrongPass123"))
