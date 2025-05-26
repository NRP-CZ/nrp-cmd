import importlib.metadata as importlib_metadata
from functools import lru_cache

from yarl import URL

from ..config import Config, RepositoryConfig
from . import base_client, connection, doi, invenio, streams
from .base_client import (
    AsyncFilesClient,
    AsyncRecordsClient,
    AsyncRepositoryClient,
    AsyncRequestsClient,
    RecordStatus,
)
from .connection import AsyncConnection
from .connection.limiter import limit_connections
from .doi import resolve_doi


@lru_cache(maxsize=1)
def async_client_classes() -> list[type[AsyncRepositoryClient]]:
    """Load all available asynchronous client classes."""
    async_client_classes: list[type[AsyncRepositoryClient]] = []
    for ep in importlib_metadata.entry_points(group="nrp_cmd.async_client"):
        async_client_classes.append(ep.load())
    return async_client_classes


async def get_async_client(
    repository: str | URL | None | RepositoryConfig,
    refresh: bool = False,
    config: Config | None = None,
) -> AsyncRepositoryClient:
    """Get an asynchronous client for the given repository.

    :param repository: the repository alias or URL
    :param refresh: whether to refresh the client configuration from the server
    :param max_connections: the maximum number of parallel connections
    :param config: the configuration to use. If not given, the configuration is loaded
    from the configuration file.
    :return: an asynchronous client for the repository
    """
    if isinstance(repository, RepositoryConfig):
        config = Config()
    if not config:
        config = Config.from_file()
    if repository is None:
        repository = config.default_alias
    if repository is None:
        raise ValueError("No repository specified and no default repository set")
    if isinstance(repository, RepositoryConfig):
        config.add_repository(repository)
        repository_config = repository
    else:
        repository_config = config.find_repository(repository)
    for async_client_class in async_client_classes():
        if await async_client_class.can_handle_repository(
            repository_config.url, verify_tls=repository_config.verify_tls
        ):
            return await async_client_class.from_configuration(
                repository_config, refresh=refresh
            )
    raise ValueError(f"No async client found for repository {repository_config.url}")


async def get_repository_from_record_id(
    connection: AsyncConnection,
    record_id: str,
    config: Config,
    repository: str | None = None,
) -> tuple[str | URL, RepositoryConfig]:
    """Try to get a repository from the record id.

    :param record_id: The record id (might be id, url, doi)
    :param config: The configuration of known repositories
    :param repository: The optional repository alias to use. If not passed in, the call will try to
                          resolve the repository from the record id.
    """
    if record_id.startswith("doi:"):
        record_id = await resolve_doi(connection, record_id[4:])
    elif record_id.startswith("https://doi.org/"):
        record_id = await resolve_doi(connection, record_id[len("https://doi.org/") :])

    if repository:
        repository_config = config.get_repository(repository)
        return record_id, repository_config

    if not record_id.startswith("https://"):
        return record_id, config.default_repository

    repository_config = config.get_repository_from_url(record_id)

    # if it is an api path, return it as it is
    record_url = URL(record_id)
    if record_url.path.startswith("/api/"):
        return record_url, repository_config

    # try to head the record to get the id
    api_url = None
    resp = await connection.head(url=record_url, get_links=True)
    for linkset in resp.getall("linkset"):
        api_url = linkset["url"]
        break

    if api_url:
        return api_url, repository_config
    else:
        return record_url, repository_config


async def resolve_record_id(
    url: str | URL,
    config: Config | None = None,
    refresh: bool = False,
) -> tuple[AsyncRepositoryClient, URL]:
    """Get an asynchronous client for the given URL."""
    if not config:
        config = Config.from_file()
    connection = AsyncConnection()
    record_url, repository_config = await get_repository_from_record_id(
        connection, str(url), config
    )
    return (
        await get_async_client(
            repository=record_url,
            refresh=refresh,
            config=config,
        ),
        URL(record_url),
    )


__all__ = (
    "get_async_client",
    "AsyncRepositoryClient",
    "connection",
    "invenio",
    "streams",
    "base_client",
    "AsyncRecordsClient",
    "AsyncFilesClient",
    "AsyncRequestsClient",
    "get_repository_from_record_id",
    "doi",
    "RecordStatus",
    "limit_connections",
    "resolve_record_id",
)
