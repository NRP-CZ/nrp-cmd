#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
from functools import partial

import pytest

from nrp_cmd.async_client import RecordStatus
from nrp_cmd.async_client.connection.task_group import Task, TaskGroup
from nrp_cmd.async_client.invenio import AsyncInvenioRepositoryClient
from nrp_cmd.errors import RepositoryCommunicationError
from nrp_cmd.progress import show_progress
from nrp_cmd.types.records import Record, RecordLinks


async def test_create(local_client: AsyncInvenioRepositoryClient):
    records_client = local_client.records
    rec = await records_client.create(
        {"title": "test"}, community="acom"
    )
    assert isinstance(rec, Record)
    assert isinstance(rec.links, RecordLinks)
    print(rec)
    assert rec.id is not None
    assert rec.metadata and rec.metadata["title"] == "test"
    assert rec.parent and rec.parent.communities["default"] is not None


@pytest.mark.skip()
async def test_create_with_default_community(local_client: AsyncInvenioRepositoryClient):
    records_client = local_client.records
    rec = await records_client.create({"metadata": {"title": "test"}})
    assert isinstance(rec, Record)


async def test_get_record(local_client: AsyncInvenioRepositoryClient):
    records_client = local_client.records
    draft_client = records_client.draft_records

    rec = await draft_client.create(
        {"title": "test"}, community="acom"
    )
    
    # read the record given the pid
    rec2 = await draft_client.read(record_id=rec.id)
    assert rec.metadata == rec2.metadata
    assert rec.id == rec2.id

    # read the record given the url
    rec3 = await draft_client.read(record_id=rec.links.self_)
    assert rec.metadata == rec3.metadata
    assert rec.id == rec3.id


async def test_remove_draft_record(local_client: AsyncInvenioRepositoryClient):
    records_client = local_client.records.draft_records
    rec = await records_client.create(
        {"title": "test"}, community="acom"
    )
    rec2 = await records_client.read(record_id=rec.id)
    assert isinstance(rec2, Record)

    await records_client.delete(rec2)
    with pytest.raises(RepositoryCommunicationError):
        await records_client.read(record_id=rec.id)


async def test_update_draft_record(local_client: AsyncInvenioRepositoryClient):
    records_client = local_client.records.draft_records
    rec = await records_client.create(
        {"metadata": {"title": "test"}}, community="acom"
    )
    created_etag = rec.get_etag()

    rec2 = await records_client.read(record_id=rec.id)
    read_etag = rec2.get_etag()

    assert read_etag == created_etag

    # perform update
    rec2.metadata["title"] = "test2"
    rec3 = await records_client.update(rec2)

    updated_etag = rec3.get_etag()
    assert read_etag != updated_etag

    rec4 = await records_client.read(record_id=rec.id)
    assert rec4.metadata["title"] == "test2"
    assert rec4.get_etag() == updated_etag


async def test_scan(local_client: AsyncInvenioRepositoryClient):
    records_client = local_client.records.draft_records
    results: list[Task] = []
    with show_progress(total=100):
        async with TaskGroup() as g:
            for i in range(100):
                results.append(
                    g.create_task(
                        lambda: records_client.create(
                            {"title": f"test {i}"}, community="acom"
                        )
                    )
                )
    record_ids = [r.result().id for r in results]

    # limit scan window to properly test it. Normally it is like 5000 records
    from nrp_cmd.async_client.invenio import records as records_module

    records_module.OPENSEARCH_SCAN_WINDOW = 20
    records_module.OPENSEARCH_SCAN_PAGE = 10

    fetched_records = []
    with show_progress():
        async with records_client.scan() as records:
            async for record in records:
                fetched_records.append(record.id)

    assert set(record_ids) <= set(fetched_records)

    # delete all records
    with show_progress(total=len(fetched_records)):
        async with TaskGroup() as g:
            for rec_id in fetched_records:
                g.create_task(
                    partial(
                        lambda rec_id: records_client.delete(
                            rec_id, status=RecordStatus.DRAFT
                        ),
                        rec_id,
                    )
                )


async def test_read_all_records(local_client: AsyncInvenioRepositoryClient):
    # create 30 records
    records_client = local_client.records.draft_records

    # limit scan window to properly test it. Normally it is like 100 records
    from nrp_cmd.async_client.invenio import records as records_module
    records_module.OPENSEARCH_SCAN_WINDOW = 5

    with show_progress():
        # remove all records that might have been left from previous tests
        fetched_records: list[Record] = []
        async with records_client.scan() as records:
            async for record in records:
                fetched_records.append(record)

    print(f"Total fetched records left from previous tests: {len(fetched_records)}")

    print("Deleting all records")
    with show_progress(total=len(fetched_records)):
        # delete records in parallel
        async with TaskGroup() as g:
            for record in fetched_records:
                g.create_task(lambda: records_client.delete(record))

    print("Creating 30 records")
    with show_progress(total=30):
        # create a bunch of records
        async with TaskGroup() as g:
            for i in range(30):
                g.create_task(
                    lambda: records_client.create({"title": f"test{1000+i}"}, community="acom")
                )

        # read all records and check if they are at least 30, that is that pagination works
        fetched_records = []

    print("Reading all records")
    with show_progress():
        async with records_client.scan() as records:
            async for record in records:
                fetched_records.append(record)

    print(f"Total fetched records: {len(fetched_records)}")
    assert len(fetched_records) >= 30

    print("Creating 10 records")
    with show_progress(total=10):
        # now create controlled records
        created_records: list[Record] = []
        for i in range(10):
            created_records.append(
                await records_client.create({"title": f"test{i}"}, community="acom")
            )

    print("Searching for new records")
    with show_progress():
        # and search
        fetched_records = (await records_client.search(q="test1")).hits.hits

        assert len(fetched_records) == 1
        f = fetched_records[0]
        assert f.metadata["title"] == "test1"

    print("Cleaning up")
    with show_progress(total=len(created_records)):
        # and clean up
        for record in created_records:
            await records_client.delete(record)


# TODO: test_patch_record