#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Local transfer."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...streams.progress import ProgressSource
from . import Transfer

if TYPE_CHECKING:
    from yarl import URL

    from ....progress import ProgressBar
    from ...connection import AsyncConnection
    from ...streams import DataSource
    from ..files import File


class LocalTransfer(Transfer):
    """Local transfer.

    This transfer copies a local file to the repository.
    The file will be stored in repository's primary storage (thus local)
    and the upload will be handled solely through the repository.
    """

    async def upload(
        self,
        connection: AsyncConnection,
        initialized_upload: File,
        source: DataSource,
        progress_bar: ProgressBar,
    ) -> None:
        """Upload the file."""
        if not initialized_upload.links.content:
            raise ValueError("The upload does not provide the content link.")

        headers = {}

        if "md5" in source.supported_checksums():
            md5_checksum = await source.checksum("md5")
            headers["Content-MD5"] = md5_checksum

        await connection.put_stream(
            url=initialized_upload.links.content,
            source=ProgressSource(source, progress_bar),
            headers=headers,
        )

    async def prepare(
        self,
        connection: AsyncConnection,
        files_link: URL,
        transfer_payload: dict,
        source: DataSource,
    ) -> None:
        """Prepare the transfer."""
        pass

    async def get_commit_payload(self, initialized_upload: File) -> dict:
        """Get payload for finalization of the successful upload."""
        return {}
