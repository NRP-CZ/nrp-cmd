#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Memory sink and source."""


import asyncio
import base64
import hashlib

from .base import DataSink, DataSource, InputStream, OutputStream, SinkState


class MemorySink(DataSink):
    """Implementation of a sink that writes data to memory."""

    def __init__(self):
        """Initialize the sink."""
        self._state = SinkState.NOT_ALLOCATED
        self._buffer = None

    async def allocate(self, size: int) -> None:
        """Allocate space for the sink."""
        self._buffer = bytearray(size)
        self._state = SinkState.ALLOCATED

    async def open_chunk(self, offset: int = 0) -> OutputStream:  # type: ignore
        """Open a chunk of the sink for writing."""
        if self._state != SinkState.ALLOCATED:
            raise RuntimeError("Sink not allocated")

        return MemoryWriter(self._buffer, offset)  # noqa

    async def close(self) -> None:
        """Close the sink."""
        self._state = SinkState.CLOSED

    @property
    def state(self) -> SinkState:
        """Return the state of the sink."""
        return self._state


class MemorySource(DataSource):
    """A data source that reads data from memory."""

    has_range_support = True

    def __init__(self, data: bytes, content_type: str):
        """Initialize the data source.

        :param data:                the data to be read
        :param content_type:        the content type of the data
        """
        self._data = data
        self._content_type = content_type

    async def open(
        self, offset: int = 0, count: int | None = None
    ) -> InputStream:
        """Open the data source for reading."""
        if count is not None:
            return MemoryReader(self._data[offset : offset + count])
        else:
            return MemoryReader(self._data[offset:])

    async def size(self) -> int: 
        """Return the size of the data."""
        return len(self._data)

    async def content_type(self) -> str:
        """Return the content type of the data."""
        return self._content_type

    async def close(self) -> None:
        """Close the data source."""
        pass

    async def checksum(
        self, algo: str = "md5", offset: int = 0, count: int | None = None
    ) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._checksum, algo, offset, count)

    def _checksum(self, algo: str, offset: int, count: int | None) -> str:
        """Calculate the checksum of the data."""
        if count is not None:
            data = self._data[offset : offset + count]
        else:
            data = self._data[offset:]

        hasher = hashlib.new(algo)
        hasher.update(data)
        return base64.b64encode(hasher.digest()).decode("ascii")

    def supported_checksums(self) -> list[str]:
        """Return a list of supported checksum algorithms."""
        return list(hashlib.algorithms_available)


class MemoryReader(InputStream):
    """A reader for in-memory data."""

    def __init__(self, data: bytes):
        """Initialize the reader.

        :param data:        the data that will be read
        """
        self._data = data

    def __len__(self):
        """Return the length of the data."""
        return len(self._data) if self._data is not None else 0

    def __bool__(self):
        """Return whether there is data to read."""
        return bool(self._data)

    def __aiter__(self):
        """We are our own iterator."""
        return self

    async def __anext__(self):
        """Simulate normal file iteration."""
        if self._data:
            ret = self._data
            self._data = None
            return ret
        else:
            raise StopAsyncIteration

    async def read(self, size: int = -1) -> bytes:
        """Read data from the buffer.

        :param size: the number of bytes to read
        :return: the data read
        """
        if self._data is None:
            return b""
        
        if size < 0:
            return await anext(self)

        size = min(size, len(self._data))
        ret = self._data[:size]
        self._data = self._data[size:]
        return ret
    
    async def close(self) -> None:
        """Close the reader."""
        pass

class MemoryWriter(OutputStream):
    """Implementation of a writer that writes data to memory."""

    def __init__(self, buffer: bytearray, offset: int):
        """Initialize the writer.

        :param buffer: The buffer where the data will be written.
        :param offset: The offset in bytes from the start of the buffer.
        """
        self._buffer = buffer
        self._offset = offset

    async def write(self, b: bytes) -> int:
        """Write data to the buffer.

        :param b: the bytes to be written
        :return:  number of bytes written
        """
        self._buffer[self._offset : self._offset + len(b)] = b
        self._offset += len(b)
        return len(b)

    async def close(self) -> None:
        """Close the writer."""
        pass
