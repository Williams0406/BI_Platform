from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from datasources.models import DataSource
from workspaces.models import Membership, Organization, Workspace

from .auth import verify_secret
from .models import GatewayJob, GatewayRegistration
from .services import (
    bind_datasource,
    claim_next_job,
    create_gateway,
    enroll_gateway,
    queue_job,
)


@override_settings(GATEWAY_ENROLLMENT_TTL_MINUTES=15, GATEWAY_JOB_LEASE_SECONDS=120)
class GatewayTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="gateway@example.com",
            password="StrongPass123",
        )
        org = Organization.objects.create(
            name="Gateway Org",
            slug="gateway-org",
            created_by=self.user,
        )
        Membership.objects.create(
            organization=org,
            user=self.user,
            role=Membership.Role.OWNER,
        )
        self.workspace = Workspace.objects.create(
            organization=org,
            name="Private",
            slug="private",
            created_by=self.user,
        )
        self.source = DataSource.objects.create(
            workspace=self.workspace,
            name="On Prem ERP",
            mode=DataSource.Mode.PRIVATE_GATEWAY,
            engine=DataSource.Engine.SQLSERVER,
            can_read=True,
            can_write=True,
            created_by=self.user,
        )

    def test_enrollment_token_is_hashed(self):
        gateway, code = create_gateway(
            self.workspace,
            "Lima Gateway",
            self.user,
        )
        enrolled, token = enroll_gateway(
            gateway.id,
            code,
            metadata={"agent_version": "1.0.0"},
        )
        self.assertNotEqual(enrolled.agent_token_hash, token)
        self.assertTrue(verify_secret(token, enrolled.agent_token_hash))
        self.assertEqual(enrolled.status, GatewayRegistration.Status.ONLINE)

    def test_queue_and_claim_job(self):
        gateway, code = create_gateway(
            self.workspace,
            "Main Gateway",
            self.user,
        )
        gateway, token = enroll_gateway(gateway.id, code)
        bind_datasource(gateway, self.source, "erp-local")
        job = queue_job(
            self.source,
            GatewayJob.Operation.READ_PAGE,
            {"schema": "dbo", "table": "orders"},
            self.user,
        )
        claimed = claim_next_job(gateway)
        self.assertIsNotNone(claimed)
        claimed_job, connection_name = claimed
        self.assertEqual(claimed_job.id, job.id)
        self.assertEqual(connection_name, "erp-local")
        self.assertEqual(claimed_job.status, GatewayJob.Status.CLAIMED)
