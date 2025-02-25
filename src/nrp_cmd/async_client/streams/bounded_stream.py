#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Bounded stream implementation."""

from typing import Any

from .base import InputStream


class BoundedStream(InputStream):
    """A stream that reads a limited amount of data from another stream."""

    def __init__(self, stream: InputStream, limit: int):
        """Initialize the stream."""
        self._stream = stream
        self._remaining = limit

    async def read(self, size: int = -1) -> bytes:
        """Read data from the stream."""
        if self._remaining <= 0:
            return b""
        if size < 0:
            size = self._remaining
        data = await self._stream.read(min(size, self._remaining))
        self._remaining -= len(data)
        return data

    def __len__(self) -> int:
        """Return the stream size."""
        return self._remaining

    def __bool__(self):
        """Return True if the stream can provide data."""
        return bool(self._remaining)

    async def close(self) -> None:
        """Close the underlying stream."""
        await self._stream.close()

    def __getattr__(self, name: str) -> Any:
        """Delegate all other calls to the underlying stream."""
        return getattr(self._stream, name)
    
    def __aiter__(self):
         return self
    
    async def __anext__(self) -> bytes:
        ret = await self.read(16384)
        if not ret:
            raise StopAsyncIteration()
        return ret
    
    