#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Local transfer."""

from __future__ import annotations

from asyncio import TaskGroup
from typing import TYPE_CHECKING

from yarl import URL

from ...connection.aws_limits import adjust_upload_multipart_params
from ...streams.progress import ProgressSource
from . import Transfer

if TYPE_CHECKING:
    from yarl import URL

    from ....progress import ProgressBar
    from ....types.files import File, MultipartUploadLinks
    from ...connection import AsyncConnection
    from ...streams import DataSource


class MultipartTransfer(Transfer):
    """Local transfer.

    This transfer copies a local file to the repository.
    The file will be stored in repository's primary storage (thus local)
    and the upload will be handled solely through the repository.
    """

    async def prepare(
        self,
        connection: AsyncConnection,
        files_link: URL,
        transfer_payload: dict,
        source: DataSource,
    ) -> None:
        """Prepare the transfer."""
        if not transfer_payload.get("size"):
            transfer_payload["size"] = await source.size()

        transfer_md = transfer_payload.get("transfer", {})

        parts, part_size = adjust_upload_multipart_params(
            transfer_payload["size"],
            transfer_md.get("parts"),
            transfer_md.get("part_size"),
        )
        transfer_md["parts"] = parts
        transfer_md["part_size"] = part_size
        
    async def upload(
        self,
        connection: AsyncConnection,
        initialized_upload: File,
        source: DataSource,
        progress_bar: ProgressBar,
    ) -> None:
        """Upload the file."""
        links: list[MultipartUploadLinks] = initialized_upload.links.parts or []
        assert links

        number_of_parts = len(links)
        part_size: int = initialized_upload.transfer.part_size

        size = initialized_upload.size
        progress_bar.set_total(size)

        async def put_stream(pt: int, start: int, count: int):
            headers: dict[str, str] = {
                "Content-Length": str(count),
                "Content-Type": "application/octet-stream",
            }
            if "md5" in source.supported_checksums():
                headers["Content-MD5"] = await source.checksum(
                    "md5", offset=start, count=count
                )
            return await connection.put_stream(
                url=links[pt].url,
                source=ProgressSource(source, progress_bar),
                open_kwargs={"offset": start, "count": count},
                headers=headers,
            )

        async with TaskGroup() as tg:
            for pt in range(number_of_parts):
                start = pt * part_size
                count = min(part_size, size - start)
                tg.create_task(put_stream(pt, start, count))

    async def get_commit_payload(self, initialized_upload: File) -> dict:
        """Get payload for finalization of the successful upload."""
        return {}
