from django.contrib.auth import get_user_model
from django.test import TestCase

from datasources.models import DataAsset, DataSource
from workspaces.models import Membership, Organization, Workspace

from .models import AssetDependency
from .services import DependencyCycleError, create_dependency, would_create_cycle


class DependencyGraphTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="deps@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Deps Org",
            slug="deps-org",
            created_by=self.user,
        )
        Membership.objects.create(
            organization=org,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        self.workspace = Workspace.objects.create(
            organization=org,
            name="BI",
            slug="bi",
            created_by=self.user,
        )
        source = DataSource.objects.create(
            workspace=self.workspace,
            name="Managed",
            mode=DataSource.Mode.MANAGED,
            engine=DataSource.Engine.PLATFORM_POSTGRES,
            can_read=True,
            can_write=True,
            can_ddl=True,
            created_by=self.user,
        )
        self.assets = []
        for name in ["A", "B", "C"]:
            self.assets.append(
                DataAsset.objects.create(
                    workspace=self.workspace,
                    data_source=source,
                    name=name,
                    asset_type=DataAsset.AssetType.TABLE,
                    physical_schema="ws_test",
                    physical_name=name.lower(),
                    created_by=self.user,
                )
            )

    def test_rejects_cycle(self):
        a, b, c = self.assets
        create_dependency(
            workspace=self.workspace,
            upstream=a,
            downstream=b,
            dependency_type=AssetDependency.DependencyType.DATA,
            refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,
        )
        create_dependency(
            workspace=self.workspace,
            upstream=b,
            downstream=c,
            dependency_type=AssetDependency.DependencyType.DATA,
            refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,
        )
        self.assertTrue(
            would_create_cycle(self.workspace.id, c.id, a.id)
        )
        with self.assertRaises(DependencyCycleError):
            create_dependency(
                workspace=self.workspace,
                upstream=c,
                downstream=a,
                dependency_type=AssetDependency.DependencyType.DATA,
                refresh_policy=AssetDependency.RefreshPolicy.MARK_STALE,
            )
