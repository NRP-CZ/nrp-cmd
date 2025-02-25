#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
from io import BytesIO
from struct import pack

import pytest

from nrp_cmd.async_client.streams import MemorySink, MemorySource
from nrp_cmd.progress import show_progress
from nrp_cmd.types.files import TRANSFER_TYPE_MULTIPART, File
from nrp_cmd.types.records import Record


async def test_list_files(local_client, draft_record: Record, draft_record_with_files: Record):
    files = local_client.files
    
    listing = await files.list(draft_record)
    assert listing == []

    listing = await files.list(draft_record_with_files)
    assert listing == []

    data = b"Hello world!"
    committed_upload = await files.upload(
        draft_record_with_files,
        key="blah.txt",
        metadata={"title": "blah"},
        source=MemorySource(data, content_type="text/plain"),
    )

    assert committed_upload.links.content is not None
    assert committed_upload.status == "completed"
    assert committed_upload.metadata["title"] == "blah"
    assert committed_upload.size == len(data)
    assert committed_upload.checksum is not None

    listing = await files.list(draft_record_with_files)
    assert len(listing) == 1
    assert listing[0].key == "blah.txt"


@pytest.mark.parametrize("data_size,parts", [(20, 5), (100, 20), (10, 10)])
async def test_multipart_upload(local_client, draft_record_with_files: Record, data_size, parts):
    # generate datasize MB of data, filled with 8bytes as an address
    files = local_client.files
    with show_progress():
        print(f"Generating {data_size}MB of data")
        io = BytesIO()
        for i in range(data_size * 1024 * 1024 // 8):
            io.write(pack(">Q", i))

        print(f"Uploading {data_size}MB of data in {parts} chunks")

        committed_upload: File = await files.upload(
            draft_record_with_files,
            key="blah.txt",
            metadata={"title": "blah"},
            source=MemorySource(io.getvalue(), content_type="text/plain"),
            transfer_type=TRANSFER_TYPE_MULTIPART,
            transfer_metadata={"parts": parts},
            progress="blah.txt",
        )

        assert committed_upload.links.content is not None
        assert committed_upload.status == "completed"
        assert committed_upload.metadata["title"] == "blah"
        assert committed_upload.size == data_size * 1024 * 1024

        assert committed_upload.transfer.type_ == "L"

        # read the file back
        print("Downloading the file back")
        sink = MemorySink()
        await files.download(committed_upload, sink, progress="blah.txt")
        assert sink._buffer == io.getvalue()