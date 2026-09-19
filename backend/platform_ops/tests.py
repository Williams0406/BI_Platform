from pathlib import Path
from django.test import SimpleTestCase, override_settings
from .storage import get_bytes, put_bytes

class LocalArtifactStoreTests(SimpleTestCase):
    @override_settings(ARTIFACT_STORAGE_BACKEND="LOCAL")
    def test_local_roundtrip(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            with override_settings(ARTIFACT_LOCAL_ROOT=Path(temp)):
                uri = put_bytes("test/a.txt", b"hello", "text/plain")
                self.assertEqual(get_bytes(uri), b"hello")
