#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#


from yarl import URL

from nrp_cmd.async_client.invenio import AsyncInvenioRepositoryClient
from nrp_cmd.types.records import Record


async def test_publish_request(
    draft_record: Record, local_client: AsyncInvenioRepositoryClient
):
    records_client = local_client.records
    requests_client = local_client.requests

    assert draft_record.files_ and draft_record.files_.enabled is False

    applicable = await requests_client.applicable_requests(draft_record)
    assert applicable.keys() == {"publish_draft"}

    request = await requests_client.create(draft_record, "publish_draft", {})
    assert request.status == "created"

    print(request.payload)
    assert request.payload is None

    requests = await requests_client.created()
    assert any(r.id == request.id for r in requests.hits)

    submitted_request = await requests_client.submit(request)
    assert submitted_request.status == "submitted"

    requests = await requests_client.submitted()
    assert any(r.id == request.id for r in requests.hits)

    accepted_request = await requests_client.accept(submitted_request)
    assert accepted_request.status == "accepted"

    requests = await requests_client.accepted()
    assert any(r.id == request.id for r in requests.hits)

    assert accepted_request.payload is not None
    assert accepted_request.payload.draft_record is None
    assert accepted_request.payload.published_record is not None
    assert accepted_request.payload.published_record.links.self_ == URL(
        f'https://127.0.0.1:5000/api/simple/{accepted_request.topic["simple"]}'
    )
