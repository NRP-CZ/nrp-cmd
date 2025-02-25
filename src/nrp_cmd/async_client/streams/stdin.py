#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Data source that reads data from standard input."""

from pathlib import Path

from .base import DataSource, InputStream
from .os import open_file


class StdInDataSource(DataSource):
    """A data source that reads data from standard input."""

    def __init__(self) -> None:
        super().__init__()
        self._opened = False

    async def open(self, offset: int = 0, count: int | None = None) -> InputStream:
        """Open the data source for reading."""
        if self._opened:
            raise RuntimeError("Cannot open the same data source multiple times.")
        self._opened = True
        if count is not None:
            raise ValueError("Cannot read a bounded stream from standard input.")
        if offset != 0:
            raise ValueError("Cannot seek in standard input.")
        ret = await open_file(Path("/sys/stdin"), mode="rb")
        return ret

    async def size(self) -> int:
        """Return the size of the data - in this case -1 as unknown."""
        return -1

    async def content_type(self) -> str:
        """Return the content type of the data."""
        return "application/octet-stream"

    async def close(self) -> None:
        """Close the data source."""
        pass

    async def checksum(
        self, algo: str = "md5", offset: int = 0, count: int | None = None
    ) -> str:
        raise NotImplementedError("Checksums are not supported for standard input.")

    def supported_checksums(self) -> list[str]:
        """Return a list of supported checksum algorithms."""
        return []
