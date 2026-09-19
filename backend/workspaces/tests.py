from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Membership, Organization


class OrganizationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="owner@example.com",
            password="StrongPass123",
        )
        self.client.force_authenticate(self.user)

    def test_creator_becomes_owner(self):
        response = self.client.post(
            "/api/v1/workspaces/organizations/",
            {"name": "Empresa Demo", "slug": "empresa-demo"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        organization = Organization.objects.get(id=response.data["id"])
        membership = Membership.objects.get(
            organization=organization,
            user=self.user,
        )
        self.assertEqual(membership.role, Membership.Role.OWNER)
