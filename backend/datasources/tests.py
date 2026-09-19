from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from workspaces.models import Membership, Organization, Workspace


class DataSourceTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="builder@example.com",
            password="StrongPass123",
        )
        self.organization = Organization.objects.create(
            name="Org",
            slug="org",
            created_by=self.user,
        )
        Membership.objects.create(
            organization=self.organization,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        self.workspace = Workspace.objects.create(
            organization=self.organization,
            name="Operations",
            slug="operations",
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def test_create_managed_datasource(self):
        response = self.client.post(
            "/api/v1/data/sources/",
            {
                "workspace": str(self.workspace.id),
                "name": "Managed Data",
                "mode": "MANAGED",
                "engine": "PLATFORM_POSTGRES",
                "can_read": True,
                "can_write": True,
                "can_ddl": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
