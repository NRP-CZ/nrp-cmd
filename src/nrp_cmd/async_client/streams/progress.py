from collections.abc import AsyncIterator
from typing import override

from ...progress import ProgressBar
from .base import DataSink, DataSource, InputStream, OutputStream, SinkState


class ProgressIterator(AsyncIterator[bytes]):
    """Iterator with progress bar."""

    def __init__(self, iterator: AsyncIterator[bytes], source: "ProgressSource"):
        """Initialize the iterator."""
        self._iterator = iterator
        self._source = source

    @override
    async def __anext__(self) -> bytes:
        data = await anext(self._iterator)
        self._source.update_progress(len(data))
        return data


class ProgressInputStream(InputStream):
    """Input stream with progress bar."""

    def __init__(self, stream: InputStream, source: "ProgressSource"):
        """Initialize the input stream."""
        self._stream = stream
        self._source = source

    @override
    async def read(self, n: int = -1) -> bytes:
        data = await self._stream.read(n)
        self._source.update_progress(len(data))
        return data

    @override
    def __aiter__(self) -> AsyncIterator[bytes]:
        return ProgressIterator(aiter(self._stream), self._source)

    @override
    def __len__(self) -> int:
        return len(self._stream)

    @override
    async def close(self) -> None:
        return await self._stream.close()


class ProgressSource(DataSource):
    """Data source with progress bar."""

    def __init__(self, source: DataSource, progress_bar: ProgressBar):
        """Create the data source."""
        self._source = source
        self._progress_bar = progress_bar
        self._output_progress = 0

    @property
    def has_range_support(self) -> bool:
        """Return whether the source supports range requests."""
        return self._source.has_range_support

    @has_range_support.setter
    def has_range_support(self, value: bool) -> None:
        """Set whether the source supports range requests."""
        raise AttributeError("Cannot set has_range_support on ProgressSource")

    @override
    async def open(self, offset: int = 0, count: int | None = None) -> InputStream:
        # reset the progress bar
        self._progress_bar.increment(-self._output_progress)
        self._output_progress = 0
        return ProgressInputStream(await self._source.open(offset, count), self)

    @override
    async def size(self) -> int:
        return await self._source.size()

    @override
    async def content_type(self) -> str:
        return await self._source.content_type()

    @override
    async def close(self) -> None:
        return await self._source.close()

    def update_progress(self, count: int) -> None:
        """Update the progress bar."""
        self._output_progress += count
        self._progress_bar.increment(count)

    @override
    async def checksum(
        self, algo: str = "md5", offset: int = 0, count: int | None = None
    ) -> str:
        return await self._source.checksum(algo, offset, count)

    @override
    def supported_checksums(self) -> list[str]:
        """Return a list of supported checksum algorithms."""
        return self._source.supported_checksums()


class ProgressSink(DataSink):
    """Data sink with progress bar."""

    def __init__(self, sink: DataSink, progress_bar: ProgressBar):
        """Create the data sink."""
        self._sink = sink
        self._progress_bar = progress_bar
        self._input_progress = 0

    @override
    async def allocate(self, size: int) -> None:
        return await self._sink.allocate(size)

    @override
    async def open_chunk(self, offset: int = 0) -> OutputStream:
        self._progress_bar.increment(-self._input_progress)
        self._input_progress = 0
        return ProgressOutputStream(await self._sink.open_chunk(offset), self)

    @override
    async def close(self) -> None:
        return await self._sink.close()

    @override
    @property
    def state(self) -> SinkState:
        return self._sink.state
    
    def update_progress(self, count: int) -> None:
        """Update the progress bar."""
        self._input_progress += count
        self._progress_bar.increment(count)


class ProgressOutputStream(OutputStream):
    """Output stream reporting progress."""
    
    def __init__(self, stream: OutputStream, sink: ProgressSink) -> None:
        """Initialize the output stream."""
        super().__init__()
        self._stream = stream
        self._sink = sink
    
    @override
    async def write(self, data: bytes) -> int:
        ret = await self._stream.write(data)
        self._sink.update_progress(ret)
        return ret

    @override
    async def close(self) -> None:
        await self._stream.close()
