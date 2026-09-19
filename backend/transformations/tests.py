from django.test import SimpleTestCase

from .sql_validation import SQLValidationError, validate_select_sql


class SQLValidationTests(SimpleTestCase):
    def test_allows_select(self):
        self.assertEqual(
            validate_select_sql("SELECT 1"),
            "SELECT 1",
        )

    def test_allows_with(self):
        sql = "WITH x AS (SELECT 1 AS a) SELECT * FROM x"
        self.assertEqual(validate_select_sql(sql), sql)

    def test_rejects_update(self):
        with self.assertRaises(SQLValidationError):
            validate_select_sql("UPDATE table_a SET x = 1")

    def test_rejects_multiple_statements(self):
        with self.assertRaises(SQLValidationError):
            validate_select_sql("SELECT 1; SELECT 2")
