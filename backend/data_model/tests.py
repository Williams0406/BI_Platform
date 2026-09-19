from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from datasources.models import DataSource
from workspaces.models import Membership, Organization, Workspace


class CatalogAccessTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="catalog@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Catalog Org",
            slug="catalog-org",
            created_by=self.user,
        )
        Membership.objects.create(
            organization=org,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        workspace = Workspace.objects.create(
            organization=org,
            name="Catalog Workspace",
            slug="catalog-workspace",
            created_by=self.user,
        )
        self.source = DataSource.objects.create(
            workspace=workspace,
            name="External PostgreSQL",
            mode=DataSource.Mode.EXTERNAL,
            engine=DataSource.Engine.POSTGRESQL,
            can_read=True,
            connection_metadata={
                "host": "localhost",
                "port": 5432,
                "database": "demo",
                "user": "reader",
            },
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def test_catalog_list_is_accessible(self):
        response = self.client.get("/api/v1/catalog/tables/")
        self.assertEqual(response.status_code, 200)
