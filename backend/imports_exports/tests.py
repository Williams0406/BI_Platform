from django.test import SimpleTestCase
from .models import ImportJob

class ImportExportDefinitionTests(SimpleTestCase):
    def test_supported_import_modes(self):
        values={choice[0] for choice in ImportJob.Mode.choices}
        self.assertEqual(values,{"APPEND","UPSERT"})
