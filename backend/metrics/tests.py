from django.contrib.auth import get_user_model
from django.test import TestCase

from data_model.models import FieldAsset, TableAsset
from datasources.models import DataAsset, DataSource
from workspaces.models import Membership, Organization, Workspace

from .models import MetricDefinition, SemanticDimension, SemanticModel
from .query_engine import MetricQueryError, render_metric_expression


class MetricExpressionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="metrics@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Metrics Org",
            slug="metrics-org",
            created_by=user,
        )
        Membership.objects.create(
            organization=org,
            user=user,
            role=Membership.Role.OWNER,
        )
        workspace = Workspace.objects.create(
            organization=org,
            name="BI",
            slug="bi",
            created_by=user,
        )
        source = DataSource.objects.create(
            workspace=workspace,
            name="Managed",
            mode=DataSource.Mode.MANAGED,
            engine=DataSource.Engine.PLATFORM_POSTGRES,
            can_read=True,
            can_write=True,
            can_ddl=True,
            created_by=user,
        )
        asset = DataAsset.objects.create(
            workspace=workspace,
            data_source=source,
            name="orders",
            asset_type=DataAsset.AssetType.TABLE,
            physical_schema="ws_test",
            physical_name="orders",
            created_by=user,
        )
        table = TableAsset.objects.create(
            data_asset=asset,
            data_source=source,
            schema_name="ws_test",
            table_name="orders",
            primary_key_columns=["id"],
        )
        total = FieldAsset.objects.create(
            table_asset=table,
            name="total",
            logical_type="DECIMAL",
            native_type="numeric(14,2)",
            ordinal_position=1,
            nullable=False,
        )
        status = FieldAsset.objects.create(
            table_asset=table,
            name="status",
            logical_type="STRING",
            native_type="varchar(40)",
            ordinal_position=2,
            nullable=False,
        )
        semantic = SemanticModel.objects.create(
            workspace=workspace,
            name="Sales",
            base_table=table,
            created_by=user,
        )
        self.metric = MetricDefinition.objects.create(
            workspace=workspace,
            semantic_model=semantic,
            name="Revenue",
            expression_type=MetricDefinition.ExpressionType.SIMPLE,
            source_field=total,
            aggregation=MetricDefinition.Aggregation.SUM,
            created_by=user,
        )
        self.status_dimension = SemanticDimension.objects.create(
            semantic_model=semantic,
            field=status,
            name="Status",
        )

    def test_simple_sum_expression(self):
        expression = render_metric_expression(self.metric)
        self.assertIn("SUM", expression)
        self.assertIn("total", expression)

    def test_sql_expression_rejects_statement(self):
        self.metric.expression_type = MetricDefinition.ExpressionType.SQL
        self.metric.expression = "SELECT SUM({{field:total}})"
        with self.assertRaises(MetricQueryError):
            render_metric_expression(self.metric)
