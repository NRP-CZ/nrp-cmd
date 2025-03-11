"""Helper functions for requests"""

from yarl import URL

from nrp_cmd.async_client import (
    AsyncRequestsClient,
    get_async_client,
    get_repository_from_record_id,
)
from nrp_cmd.async_client.connection import AsyncConnection
from nrp_cmd.config import Config


async def resolve_request(
    request_id: str, config: Config, repository: str | None = None
) -> tuple[AsyncRequestsClient, URL]:

    connection = AsyncConnection()

    final_request_id, repository_config = await get_repository_from_record_id(
        connection, request_id, config, repository
    )

    config.add_repository(repository_config)
    repository_client = await get_async_client(repository, config=config)

    request_url: URL
    if isinstance(final_request_id, str):
        if final_request_id.startswith("https://"):
            request_url = URL(final_request_id)
        else:
            request_url = repository_config.requests_url / final_request_id
    else:
        request_url = final_request_id

    return repository_client.requests, request_url
