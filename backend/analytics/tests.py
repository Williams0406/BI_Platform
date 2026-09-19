from django.contrib.auth import get_user_model
from django.test import TestCase

from data_model.models import FieldAsset, TableAsset
from datasources.models import DataAsset, DataSource
from metrics.models import MetricDefinition, SemanticDimension, SemanticModel
from workspaces.models import Membership, Organization, Workspace

from .models import ChartDefinition, DashboardDefinition, DashboardItem


class AnalyticsModelTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="analytics@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Analytics Org",
            slug="analytics-org",
            created_by=user,
        )
        Membership.objects.create(
            organization=org,
            user=user,
            role=Membership.Role.OWNER,
        )
        workspace = Workspace.objects.create(
            organization=org,
            name="Analytics",
            slug="analytics",
            created_by=user,
        )
        source = DataSource.objects.create(
            workspace=workspace,
            name="Managed",
            mode=DataSource.Mode.MANAGED,
            engine=DataSource.Engine.PLATFORM_POSTGRES,
            created_by=user,
        )
        asset = DataAsset.objects.create(
            workspace=workspace,
            data_source=source,
            name="sales",
            asset_type=DataAsset.AssetType.TABLE,
            physical_schema="ws_test",
            physical_name="sales",
            created_by=user,
        )
        table = TableAsset.objects.create(
            data_asset=asset,
            data_source=source,
            schema_name="ws_test",
            table_name="sales",
        )
        amount = FieldAsset.objects.create(
            table_asset=table,
            name="amount",
            logical_type="DECIMAL",
            native_type="numeric",
            ordinal_position=1,
        )
        category = FieldAsset.objects.create(
            table_asset=table,
            name="category",
            logical_type="STRING",
            native_type="varchar",
            ordinal_position=2,
        )
        semantic = SemanticModel.objects.create(
            workspace=workspace,
            name="Sales semantic",
            base_table=table,
            created_by=user,
        )
        self.dimension = SemanticDimension.objects.create(
            semantic_model=semantic,
            field=category,
            name="Category",
        )
        metric = MetricDefinition.objects.create(
            workspace=workspace,
            semantic_model=semantic,
            name="Revenue",
            source_field=amount,
            aggregation=MetricDefinition.Aggregation.SUM,
            created_by=user,
        )
        self.chart = ChartDefinition.objects.create(
            workspace=workspace,
            name="Revenue by category",
            chart_type=ChartDefinition.ChartType.BAR,
            metric=metric,
            created_by=user,
        )
        self.chart.dimensions.add(self.dimension)
        self.dashboard = DashboardDefinition.objects.create(
            workspace=workspace,
            name="Sales Dashboard",
            created_by=user,
        )

    def test_dashboard_accepts_chart(self):
        item = DashboardItem.objects.create(
            dashboard=self.dashboard,
            chart=self.chart,
            position={"x": 0, "y": 0, "w": 6, "h": 4},
        )
        self.assertEqual(item.dashboard, self.dashboard)
