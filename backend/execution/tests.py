from django.contrib.auth import get_user_model
from django.test import TestCase

from workspaces.models import Membership, Organization, Workspace

from .models import Execution
from .services import create_execution, mark_running, mark_success


class ExecutionLifecycleTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="execution@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Execution Org",
            slug="execution-org",
            created_by=user,
        )
        Membership.objects.create(
            organization=org,
            user=user,
            role=Membership.Role.OWNER,
        )
        self.workspace = Workspace.objects.create(
            organization=org,
            name="Execution Workspace",
            slug="execution-workspace",
            created_by=user,
        )
        self.user = user

    def test_lifecycle(self):
        execution = create_execution(
            workspace=self.workspace,
            object_type=Execution.ObjectType.GENERIC,
            requested_by=self.user,
        )
        self.assertEqual(execution.status, Execution.Status.QUEUED)

        mark_running(execution)
        execution.refresh_from_db()
        self.assertEqual(execution.status, Execution.Status.RUNNING)

        mark_success(execution, {"ok": True})
        execution.refresh_from_db()
        self.assertEqual(execution.status, Execution.Status.SUCCESS)
        self.assertEqual(execution.progress, 100)
