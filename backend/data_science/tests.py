from django.contrib.auth import get_user_model
from django.test import TestCase
from data_model.models import FieldAsset, TableAsset
from datasources.models import DataAsset, DataSource
from workspaces.models import Membership, Organization, Workspace
from .ml_services import validate_algorithm_task
from .models import DatasetDefinition, ModelDefinition

class ModelValidationTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user(email="ds@example.com",password="StrongPass123")
        org=Organization.objects.create(name="DS Org",slug="ds-org",created_by=user)
        Membership.objects.create(organization=org,user=user,role=Membership.Role.OWNER)
        workspace=Workspace.objects.create(organization=org,name="DS",slug="ds",created_by=user)
        source=DataSource.objects.create(workspace=workspace,name="Managed",mode=DataSource.Mode.MANAGED,engine=DataSource.Engine.PLATFORM_POSTGRES,created_by=user)
        asset=DataAsset.objects.create(workspace=workspace,data_source=source,name="training",asset_type=DataAsset.AssetType.TABLE,physical_schema="ws_test",physical_name="training",created_by=user)
        table=TableAsset.objects.create(data_asset=asset,data_source=source,schema_name="ws_test",table_name="training")
        feature=FieldAsset.objects.create(table_asset=table,name="x",logical_type="FLOAT",native_type="double precision",ordinal_position=1)
        target=FieldAsset.objects.create(table_asset=table,name="y",logical_type="FLOAT",native_type="double precision",ordinal_position=2)
        dataset=DatasetDefinition.objects.create(workspace=workspace,name="Training",source_table=table,created_by=user)
        self.model=ModelDefinition.objects.create(workspace=workspace,dataset=dataset,name="Regression",task_type=ModelDefinition.TaskType.REGRESSION,algorithm=ModelDefinition.Algorithm.LINEAR_REGRESSION,target=target,created_by=user)
        self.model.features.add(feature)
    def test_matching_algorithm_task(self):
        validate_algorithm_task(self.model)
    def test_rejects_classifier_for_regression(self):
        self.model.algorithm=ModelDefinition.Algorithm.LOGISTIC_REGRESSION
        with self.assertRaises(ValueError): validate_algorithm_task(self.model)
