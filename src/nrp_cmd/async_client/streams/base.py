#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Protocol for data sources and sinks."""

from collections.abc import AsyncIterator
from enum import StrEnum, auto
from typing import Protocol, runtime_checkable


@runtime_checkable
class InputStream(Protocol):
    """Protocol for data readers."""

    async def read(self, n: int = -1) -> bytes:
        """Read up to n bytes from the stream."""
        ...
        
    def __aiter__(self) -> AsyncIterator[bytes]:
        """Return an async iterator returning chunks of the stream."""
        ...

    async def close(self) -> None:
        """Close the stream."""
        ...

    def __len__(self) -> int:
        """Return the length of the stream."""
        ...


@runtime_checkable
class OutputStream(Protocol):
    """Protocol for data writers."""

    async def write(self, data: bytes) -> int:
        ...

    async def close(self) -> None:
        ...


class SinkState(StrEnum):
    """State of the sink."""

    NOT_ALLOCATED = auto()
    """Sink's space has not been allocated yet."""
    ALLOCATED = auto()
    """Sink's space has been allocated and reserved on the filesystem/memory."""
    CLOSED = auto()
    """Sink has been closed."""


@runtime_checkable
class DataSink(Protocol):
    """Protocol for data sinks."""

    async def allocate(self, size: int) -> None:
        """Allocate space for the sink.

        :param size: The size of the sink in bytes.
        """
        ...

    async def open_chunk(self, offset: int = 0) -> OutputStream:
        """Get a writer for the sink, starting at the given offset.

        :param offset: The offset in bytes from the start of the sink.
        :return: A writer for the sink.
        """
        ...

    async def close(self) -> None:
        """Close the sink and all unclosed writers."""
        ...

    @property
    def state(self) -> SinkState:
        """Return the current state of the sink."""
        ...


@runtime_checkable
class DataSource(Protocol):
    """Protocol for data sources."""

    has_range_support: bool = False

    async def open(self, offset: int = 0, count: int | None = None) -> InputStream:
        """Open the data source for reading.

        :param offset:      where to start reading from
        :param count:       how many bytes to read, if None, read until the end
        :return:            a reader for the data source
        """
        ...

    async def checksum(
        self, algo: str = "md5", offset: int = 0, count: int | None = None
    ) -> str:
        """Return the checksum of the (portion of) source.

        :param algo: The checksum algorithm to use.
        :param offset: The offset in bytes from the start of the source.
        :param count: The number of bytes to include in the checksum.
        :return The checksum of the stream or None if the implementation does not support checksums.
        """
        ...

    def supported_checksums(self) -> list[str]:
        """Return a list of supported checksum algorithms."""
        ...

    async def size(self) -> int:
        """Return the length of the data source in bytes."""
        ...

    async def content_type(self) -> str:
        """Return the content type of the data source."""
        ...

    async def close(self) -> None:
        """Close the data source."""
        ...
