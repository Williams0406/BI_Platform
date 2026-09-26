from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from common.code_deletion import delete_code_and_measures
from common.models import ScriptArtifact, ScriptBlock
from metrics.models import MetricDefinition
from metrics import tests as metric_test_fixtures
from workspaces.models import Workspace


class CodeDeletionTests(TestCase):
    def setUp(self):
        metric_test_fixtures.MetricExpressionTests.setUp(self)
        self.metric.expression_type = "DAX"
        self.metric.expression = "SUM([total])"
        self.metric.save()
        self.client = APIClient()
        self.client.force_authenticate(self.metric.created_by)

    def block(self, **overrides):
        values = dict(workspace=self.metric.workspace, created_by=self.metric.created_by,
                      name="Revenue", language="DAX", code="Revenue = SUM([total])",
                      linked_object_type="METRIC", linked_object_id=str(self.metric.id))
        values.update(overrides)
        return ScriptBlock.objects.create(**values)

    def test_script_delete_removes_measure_and_all_owning_blocks(self):
        first = self.block()
        second = self.block(name="Previous version")
        reference = self.block(name="Reference", code="Other = [Revenue] * 2", linked_object_type="", linked_object_id="")
        response = self.client.delete(f"/api/v1/scripts/{first.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data["deleted_script_ids"]), {str(first.id), str(second.id)})
        self.assertFalse(MetricDefinition.objects.filter(id=self.metric.id).exists())
        self.assertTrue(ScriptBlock.objects.filter(id=reference.id).exists())

    def test_metric_delete_removes_code_and_artifacts(self):
        block = self.block()
        ScriptArtifact.objects.create(script_block=block, artifact_type="MEASURE", name="Revenue")
        response = self.client.delete(f"/api/v1/metrics/{self.metric.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScriptBlock.objects.filter(id=block.id).exists())
        self.assertFalse(ScriptArtifact.objects.filter(script_block_id=block.id).exists())
        self.assertIn(str(self.metric.id), response.data["deleted_metric_ids"])

    def test_plain_block_does_not_delete_measure_by_name(self):
        block = self.block(linked_object_type="", linked_object_id="", code="Revenue = 7")
        self.client.delete(f"/api/v1/scripts/{block.id}/")
        self.assertTrue(MetricDefinition.objects.filter(id=self.metric.id).exists())

    def test_exact_legacy_definition_is_linked(self):
        block = self.block(linked_object_type="", linked_object_id="")
        self.client.delete(f"/api/v1/scripts/{block.id}/")
        self.assertFalse(MetricDefinition.objects.filter(id=self.metric.id).exists())

    def test_cross_workspace_link_cannot_delete_metric(self):
        workspace = Workspace.objects.create(organization=self.metric.workspace.organization,
                                             name="Other", slug="other", created_by=self.metric.created_by)
        block = self.block(workspace=workspace)
        self.client.delete(f"/api/v1/scripts/{block.id}/")
        self.assertTrue(MetricDefinition.objects.filter(id=self.metric.id).exists())

    def test_deletion_rolls_back_when_cleanup_fails(self):
        block = self.block()
        with patch("common.code_deletion.DataAsset.objects.filter", side_effect=RuntimeError("cleanup failed")):
            with self.assertRaises(RuntimeError):
                delete_code_and_measures(workspace_id=self.metric.workspace_id, script_id=block.id)
        self.assertTrue(ScriptBlock.objects.filter(id=block.id).exists())
        self.assertTrue(MetricDefinition.objects.filter(id=self.metric.id).exists())

    def test_artifact_ownership_is_deleted(self):
        block = self.block(code="x = 1", linked_object_type="", linked_object_id="")
        ScriptArtifact.objects.create(script_block=block, artifact_type="MEASURE", name="Revenue",
                                      object_type="METRIC", object_id=str(self.metric.id))
        self.client.delete(f"/api/v1/scripts/{block.id}/")
        self.assertFalse(MetricDefinition.objects.filter(id=self.metric.id).exists())
