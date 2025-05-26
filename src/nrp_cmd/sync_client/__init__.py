import importlib.metadata as importlib_metadata
from functools import lru_cache

from yarl import URL

from ..config import Config, RepositoryConfig
from . import base_client, connection, doi, invenio, streams
from .base_client import RecordStatus, SyncRepositoryClient
from .connection import SyncConnection
from .doi import resolve_doi


@lru_cache(maxsize=1)
def sync_client_classes() -> list[type[SyncRepositoryClient]]:
    """Load all available synchronous client classes."""
    sync_client_classes: list[type[SyncRepositoryClient]] = []
    for ep in importlib_metadata.entry_points(group="nrp_cmd.sync_client"):
        sync_client_classes.append(ep.load())
    return sync_client_classes


def get_sync_client(
    repository: str | URL | RepositoryConfig,
    refresh: bool = False,
    config: Config | None = None,
) -> SyncRepositoryClient:
    """Get a synchronous client for the given repository.

    :param repository: the repository alias or URL
    :param refresh: whether to refresh the client configuration from the server
    :param max_connections: the maximum number of parallel connections
    :param config: the configuration to use. If not given, the configuration is loaded
    from the configuration file.
    :return: a synchronous client for the repository
    """
    if isinstance(repository, RepositoryConfig):
        config = Config()
    if not config:
        config = Config.from_file()

    if isinstance(repository, RepositoryConfig):
        config.add_repository(repository)
        repository_config = repository
    else:
        repository_config = config.find_repository(repository)

    for sync_client_class in sync_client_classes():
        if sync_client_class.can_handle_repository(
            repository_config.url, verify_tls=repository_config.verify_tls
        ):
            return sync_client_class.from_configuration(
                repository_config, refresh=refresh
            )
    raise ValueError(f"No sync client found for repository {repository_config.url}")


def get_repository_from_record_id(
    connection: connection.SyncConnection,
    record_id: str,
    config: Config,
    repository: str | None = None,
) -> tuple[str, RepositoryConfig]:
    """Try to get a repository from the record id.

    :param record_id: The record id (might be id, url, doi)
    :param config: The configuration of known repositories
    :param repository: The optional repository alias to use. If not passed in, the call will try to
                          resolve the repository from the record id.
    """
    if record_id.startswith("doi:"):
        record_id = resolve_doi(connection, record_id[4:])
    elif record_id.startswith("https://doi.org/"):
        record_id = resolve_doi(connection, record_id[len("https://doi.org/") :])

    if repository:
        repository_config = config.get_repository(repository)
        return record_id, repository_config

    if not record_id.startswith("https://"):
        return record_id, config.default_repository

    repository_config = config.get_repository_from_url(record_id)

    # if it is an api path, return it as it is
    record_url = URL(record_id)
    if record_url.path.startswith("/api/"):
        return str(record_id), repository_config

    # try to head the record to get the id
    api_url = None
    resp = connection.head(url=record_url, get_links=True)
    if "linkset" in resp:
        api_url = resp["linkset"]

    if api_url:
        return str(api_url), repository_config
    else:
        return str(record_url), repository_config


def resolve_record_id(
    url: str | URL,
    config: Config | None = None,
    refresh: bool = False,
) -> tuple[SyncRepositoryClient, URL]:
    """Get an asynchronous client for the given URL."""
    if not config:
        config = Config.from_file()
    connection = SyncConnection()
    record_url, repository_config = get_repository_from_record_id(
        connection, str(url), config
    )
    return (
        get_sync_client(
            repository=record_url,
            refresh=refresh,
            config=config,
        ),
        URL(record_url),
    )


__all__ = (
    "get_sync_client",
    "SyncRepositoryClient",
    "connection",
    "invenio",
    "streams",
    "base_client",
    "doi",
    "get_repository_from_record_id",
    "RecordStatus",
    "resolve_record_id",
)
