
import pytest

from nrp_cmd.async_client.invenio import AsyncInvenioRepositoryClient
from nrp_cmd.types.records import Record


@pytest.fixture()
async def local_client(local_repository_config) -> AsyncInvenioRepositoryClient:
    ret = await AsyncInvenioRepositoryClient.from_configuration(local_repository_config)
    return ret

@pytest.fixture()
async def zenodo_client(zenodo_repository_config) -> AsyncInvenioRepositoryClient:
    ret = await AsyncInvenioRepositoryClient.from_configuration(zenodo_repository_config)
    return ret


@pytest.fixture(scope="function")
async def draft_record(request, local_client: AsyncInvenioRepositoryClient) -> Record:
    records_client = local_client.records
    return await records_client.create(
        {
            "title": f"async draft record for {request.node.name}",
        },
        community="acom",
        files_enabled=False,
    )


@pytest.fixture(scope="function")
async def draft_record_with_files(request, local_client) -> Record:
    records_client = local_client.records
    return await records_client.create(
        {
            "title": f"async draft record for {request.node.name}",
        },
        community="acom",
        files_enabled=True,
    )

@pytest.fixture(scope="function", autouse=True)
def reset_limiter() -> None:
    from nrp_cmd.async_client.connection.limiter import current_limiter

    current_limiter.reset()
