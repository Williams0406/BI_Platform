from django.test import SimpleTestCase

from .exceptions import ConnectorConfigurationError
from .postgresql import PostgreSQLConnector
from .sqlserver import SQLServerConnector


class ConnectorConfigurationTests(SimpleTestCase):
    def test_postgres_requires_connection_fields(self):
        with self.assertRaises(ConnectorConfigurationError):
            PostgreSQLConnector({})

    def test_postgres_quotes_identifiers(self):
        connector = PostgreSQLConnector(
            {
                "host": "localhost",
                "database": "db",
                "user": "user",
            }
        )
        self.assertEqual(connector.quote_identifier('a"b'), '"a""b"')

    def test_sqlserver_quotes_identifiers(self):
        connector = SQLServerConnector(
            {
                "server": "localhost",
                "database": "db",
                "trusted_connection": True,
            }
        )
        self.assertEqual(connector.quote_identifier("a]b"), "[a]]b]")
