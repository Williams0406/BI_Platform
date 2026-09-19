from datasources.models import DataSource

from .exceptions import ConnectorNotSupportedError
from .postgresql import PostgreSQLConnector
from .sqlserver import SQLServerConnector


CONNECTOR_REGISTRY = {
    DataSource.Engine.POSTGRESQL: PostgreSQLConnector,
    DataSource.Engine.SQLSERVER: SQLServerConnector,
}


def get_connector_class(engine: str):
    connector_class = CONNECTOR_REGISTRY.get(engine)
    if connector_class is None:
        raise ConnectorNotSupportedError(
            f"No existe un connector registrado para engine={engine}."
        )
    return connector_class


def build_connector(data_source: DataSource, runtime_credentials=None):
    """
    Merge non-secret connection metadata persisted on DataSource with
    runtime credentials supplied for the current request/job.

    Secrets are intentionally not persisted in Phase 3.
    """
    config = dict(data_source.connection_metadata or {})

    # Phase 10: stored credentials are encrypted by Governance.
    # Runtime credentials always take precedence, useful for one-off tests.
    if not runtime_credentials:
        try:
            from governance.services import decrypt_secret_payload
            secret = data_source.encrypted_secret
            config.update(decrypt_secret_payload(secret))
        except Exception as exc:
            # Absence of a stored secret is valid; connector validation will
            # report missing credentials when they are actually required.
            if exc.__class__.__name__ not in {
                "RelatedObjectDoesNotExist",
                "ObjectDoesNotExist",
            }:
                from governance.models import EncryptedSecret
                if EncryptedSecret.objects.filter(data_source=data_source).exists():
                    raise

    config.update(runtime_credentials or {})
    return get_connector_class(data_source.engine)(config)
