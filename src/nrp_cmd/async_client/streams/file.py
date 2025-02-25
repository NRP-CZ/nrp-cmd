#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""File sources and sinks."""

import contextlib
import hashlib
from pathlib import Path
from typing import override

import magic

from .base import DataSink, DataSource, InputStream, OutputStream, SinkState
from .bounded_stream import BoundedStream
from .os import FileOutputStream, checksum_file, file_stat, open_file


class FileSink(DataSink):
    """Implementation of a sink that writes data to filesystem."""

    def __init__(self, fpath: Path):
        """Initialize the sink.

        :param fpath: The path to the file where the data will be written.
        """
        self._fpath = fpath
        self._state = SinkState.NOT_ALLOCATED
        self._file: FileOutputStream | None = None

    @override
    async def allocate(self, size: int) -> None:
        """Allocate space for the sink."""
        self._file = await open_file(self._fpath, mode="wb")
        await self._file.truncate(size)
        self._state = SinkState.ALLOCATED

    @override
    async def open_chunk(self, offset: int = 0) -> OutputStream:  # type: ignore
        """Open a chunk of the sink for writing."""
        if self._state != SinkState.ALLOCATED:
            raise RuntimeError("Sink not allocated")

        chunk = await open_file(self._fpath, mode="r+b")
        await chunk.seek(offset)
        return chunk

    @override
    async def close(self) -> None:
        """Close the sink."""
        if self._file is not None:
            with contextlib.suppress(Exception):
                await self._file.close()
        self._file = None

        self._state = SinkState.CLOSED

    @override
    @property
    def state(self) -> SinkState:
        """Return the current state of the sink."""
        return self._state

    def __repr__(self):
        """Return a string representation of the sink."""
        return f"<{self.__class__.__name__} {self._fpath} {self._state}>"


class FileSource(DataSource):
    """A data source that reads data from a file."""

    has_range_support = True

    def __init__(self, file_name: Path | str):
        """Initialize the data source.

        :param file_name: The name of the file to read from, must exist on the filesystem
        """
        if isinstance(file_name, str):
            file_name = Path(file_name)
        self._file_name = file_name

    @override
    async def open(self, offset: int = 0, count: int | None = None) -> InputStream:  # type: ignore
        """Open the file for reading."""
        ret = await open_file(self._file_name, mode="rb")
        await ret.seek(offset)
        if not count:
            return BoundedStream(ret, await self.size())
        else:
            return BoundedStream(ret, count)

    @override
    async def size(self) -> int:
        """Return the size of the file."""
        return (await file_stat(self._file_name)).st_size

    @override
    async def content_type(self) -> str:
        """Return the content type of the file."""
        f = await open_file(self._file_name, mode="rb")
        try:
            data = await f.read(2048)
            return magic.from_buffer(data, mime=True)
        finally:
            await f.close()

    @override
    async def close(self) -> None:
        """Close the data source."""
        pass

    @override
    async def checksum(
        self, algo: str = "md5", offset: int = 0, count: int | None = None
    ) -> str:
        return await checksum_file(self._file_name, algo, offset, count)

    @override
    def supported_checksums(self) -> list[str]:
        """Return a list of supported checksum algorithms."""
        return list(hashlib.algorithms_available)
