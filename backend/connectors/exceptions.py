class ConnectorError(Exception):
    """Base error for datasource connectors."""


class ConnectorConfigurationError(ConnectorError):
    """Invalid or insufficient connection configuration."""


class ConnectorConnectionError(ConnectorError):
    """Connection to external database could not be established."""


class ConnectorQueryError(ConnectorError):
    """A query executed by a connector failed."""


class ConnectorNotSupportedError(ConnectorError):
    """Datasource engine has no connector implementation."""
