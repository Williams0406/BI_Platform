from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings
from cryptography.fernet import Fernet
from workspaces.models import Organization,Workspace
from .models import WorkspaceQuota
from .services import decrypt_secret_payload,encrypt_secret_payload,get_quota

class GovernanceTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(email="gov@example.com",password="StrongPass123")
        org=Organization.objects.create(name="Gov Org",slug="gov-org",created_by=self.user)
        self.workspace=Workspace.objects.create(organization=org,name="Gov",slug="gov",created_by=self.user)
    def test_default_quota(self):
        quota=get_quota(self.workspace)
        self.assertGreater(quota.max_import_rows,0)

    @override_settings(GOVERNANCE_FERNET_KEY=Fernet.generate_key().decode())
    def test_secret_roundtrip(self):
        from .models import EncryptedSecret
        encrypted=encrypt_secret_payload({"password":"abc"})
        secret=EncryptedSecret(workspace=self.workspace,name="x",ciphertext=encrypted,created_by=self.user)
        self.assertEqual(decrypt_secret_payload(secret)["password"],"abc")
