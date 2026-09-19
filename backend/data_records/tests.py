from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from datasources.models import DataAsset, DataSource
from data_model.models import FieldAsset, TableAsset
from workspaces.models import Membership, Organization, Workspace

from .validators import validate_record_payload
from .exceptions import RecordValidationError


class RecordValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="records@example.com",
            password="StrongPass123",
        )
        self.org = Organization.objects.create(
            name="Records Org",
            slug="records-org",
            created_by=self.user,
        )
        Membership.objects.create(
            organization=self.org,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        self.workspace = Workspace.objects.create(
            organization=self.org,
            name="Ops",
            slug="ops",
            created_by=self.user,
        )
        self.source = DataSource.objects.create(
            workspace=self.workspace,
            name="Managed Database",
            mode=DataSource.Mode.MANAGED,
            engine=DataSource.Engine.PLATFORM_POSTGRES,
            status=DataSource.Status.ACTIVE,
            can_read=True,
            can_write=True,
            can_ddl=True,
            created_by=self.user,
        )
        self.asset = DataAsset.objects.create(
            workspace=self.workspace,
            data_source=self.source,
            name="orders",
            asset_type=DataAsset.AssetType.TABLE,
            physical_schema="ws_test",
            physical_name="orders",
            created_by=self.user,
        )
        self.table = TableAsset.objects.create(
            data_asset=self.asset,
            data_source=self.source,
            schema_name="ws_test",
            table_name="orders",
            primary_key_columns=["id"],
            row_version_column="__row_version",
        )
        FieldAsset.objects.create(
            table_asset=self.table,
            name="id",
            logical_type="INTEGER",
            native_type="integer",
            ordinal_position=1,
            nullable=False,
            is_primary_key=True,
        )
        FieldAsset.objects.create(
            table_asset=self.table,
            name="status",
            logical_type="STRING",
            native_type="varchar(20)",
            ordinal_position=2,
            nullable=False,
            max_length=20,
        )

    def test_rejects_unknown_field(self):
        with self.assertRaises(RecordValidationError):
            validate_record_payload(
                self.table,
                {"id": 1, "status": "NEW", "unknown": "x"},
            )

    def test_accepts_valid_record(self):
        result = validate_record_payload(
            self.table,
            {"id": 1, "status": "NEW"},
        )
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["status"], "NEW")
