from django.contrib.auth import get_user_model
from django.test import TestCase

from data_model.models import FieldAsset, TableAsset
from datasources.models import DataAsset, DataSource
from workspaces.models import Membership, Organization, Workspace

from .models import ViewDefinition, ViewFieldBinding
from .services import translate_interaction, validate_view_contract


class ViewEngineContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="views@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Views Org",
            slug="views-org",
            created_by=self.user,
        )
        Membership.objects.create(
            organization=org,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        workspace = Workspace.objects.create(
            organization=org,
            name="Ops",
            slug="ops",
            created_by=self.user,
        )
        source = DataSource.objects.create(
            workspace=workspace,
            name="Managed Database",
            mode=DataSource.Mode.MANAGED,
            engine=DataSource.Engine.PLATFORM_POSTGRES,
            status=DataSource.Status.ACTIVE,
            can_read=True,
            can_write=True,
            can_ddl=True,
            created_by=self.user,
        )
        asset = DataAsset.objects.create(
            workspace=workspace,
            data_source=source,
            name="tasks",
            asset_type=DataAsset.AssetType.TABLE,
            physical_schema="ws_test",
            physical_name="tasks",
            created_by=self.user,
        )
        table = TableAsset.objects.create(
            data_asset=asset,
            data_source=source,
            schema_name="ws_test",
            table_name="tasks",
            primary_key_columns=["id"],
            row_version_column="__row_version",
        )
        self.title = FieldAsset.objects.create(
            table_asset=table,
            name="title",
            logical_type="STRING",
            native_type="varchar(255)",
            ordinal_position=1,
            nullable=False,
        )
        self.status = FieldAsset.objects.create(
            table_asset=table,
            name="status",
            logical_type="STRING",
            native_type="varchar(40)",
            ordinal_position=2,
            nullable=False,
        )
        self.view = ViewDefinition.objects.create(
            workspace=workspace,
            source_table=table,
            name="Tasks Kanban",
            view_type=ViewDefinition.ViewType.KANBAN,
            created_by=self.user,
        )

    def test_kanban_contract_requires_title_and_status(self):
        self.assertFalse(validate_view_contract(self.view)["valid"])

        ViewFieldBinding.objects.create(
            view=self.view,
            field=self.title,
            role=ViewFieldBinding.BindingRole.TITLE,
        )
        ViewFieldBinding.objects.create(
            view=self.view,
            field=self.status,
            role=ViewFieldBinding.BindingRole.STATUS,
            editable=True,
        )

        self.assertTrue(validate_view_contract(self.view)["valid"])

    def test_kanban_move_only_allows_status_binding(self):
        ViewFieldBinding.objects.create(
            view=self.view,
            field=self.title,
            role=ViewFieldBinding.BindingRole.TITLE,
        )
        ViewFieldBinding.objects.create(
            view=self.view,
            field=self.status,
            role=ViewFieldBinding.BindingRole.STATUS,
            editable=True,
        )

        result = translate_interaction(
            self.view,
            "MOVE_KANBAN",
            {"status": "DONE"},
        )
        self.assertEqual(result, {"status": "DONE"})

        with self.assertRaises(ValueError):
            translate_interaction(
                self.view,
                "MOVE_KANBAN",
                {"title": "Unauthorized"},
            )

class OperationalQueryPlannerSmokeTests(TestCase):
    """The detailed SQL execution is covered by integration tests with managed schemas.
    This smoke test keeps the planner module importable during Django test discovery.
    """
    def test_operational_query_planner_imports(self):
        from views_engine.operational_query import build_operational_plan, execute_operational_plan
        self.assertTrue(callable(build_operational_plan))
        self.assertTrue(callable(execute_operational_plan))
