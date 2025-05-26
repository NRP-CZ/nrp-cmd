"""Test Zenodo integration with this library."""

import pytest


@pytest.fixture()
async def zenodo_client():
    """Fixture to create a Zenodo client."""
    from nrp_cmd.async_client import get_async_client
    return await get_async_client("https://zenodo.org")

async def test_info(zenodo_client):
    info = await zenodo_client.get_repository_info(refresh=True)
    assert info.version == "Zenodo"
    print(info)
    
async def test_get_record(zenodo_client):
    """Test fetching a specific record from Zenodo."""
    record_id = "819496"  # Replace with a valid Zenodo record ID
    record = await zenodo_client.records.read(record_id)
    assert record.id == record_id
    assert record.metadata["title"] is not None
    print(record)
    
async def test_search_records(zenodo_client):
    """Test searching for records in Zenodo."""
    search_results = await zenodo_client.records.search(q="title:test", size=5)
    assert len(search_results) == 5
    for record in search_results:
        assert "test" in record.metadata["title"].lower()
    search_results = await zenodo_client.records.search(q="title:precipitation", size=10)
    assert len(search_results) == 10
