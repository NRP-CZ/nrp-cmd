from pathlib import Path
from typing import Any, overload, override

from yarl import URL

from ...progress import DummyProgressBar, current_progress
from ...types.files import TRANSFER_TYPE_LOCAL, File, FilesAPIList, FilesList
from ...types.info import RepositoryInfo
from ...types.records import Record
from ..base_client import AsyncFilesClient
from ..connection import AsyncConnection
from ..streams import DataSink, DataSource


class AsyncInvenioFilesClient(AsyncFilesClient):
    """Invenio files client."""

    def __init__(self, connection: AsyncConnection, info: RepositoryInfo):
        """Initialize the client."""
        self._connection = connection
        self._info = info

    @override
    async def list(
        self,
        record_or_url: Record | URL,
    ) -> list[File]:
        """List the files of a record."""
        files_url = self._get_files_url(record_or_url)
        files_list = await self._connection.get(url=files_url, result_class=FilesList)
        return FilesAPIList(files_list.entries)

    @override
    @overload
    async def read(self, file_url: URL) -> File: ...

    @override
    @overload
    async def read(self, record: Record, key: str) -> File: ...

    @override
    @overload
    async def read(self, record_url: URL, key: str) -> File: ...

    @override  # type: ignore
    async def read(
        self,
        *args: Record | URL | str,
    ):
        if len(args) == 1:
            assert isinstance(args[0], URL), "Invalid argument - expecting a file URL"
            file_url: URL = args[0]
        elif len(args) == 2:
            assert isinstance(
                args[0], Record
            ), "Invalid argument - expecting a record as the first argument"
            record_or_url: Record | URL = args[0]
            assert isinstance(
                args[1], str
            ), "Invalid argument - expecting a string key as the second argument"
            key: str = args[1]

            files_url = self._get_files_url(record_or_url)
            file_url = files_url / key

        return await self._connection.get(url=file_url, result_class=File)

    @override
    async def update(self, file: File) -> File:
        """Update the file metadata in the repository.

        :param file: file to update
        """
        return await self._connection.put(
            url=file.links.self_, json={"metadata": file.metadata}, result_class=File
        )

    @override
    async def upload(
        self,
        record_or_url: Record | URL,
        key: str,
        metadata: dict[str, Any],
        source: DataSource | str | Path,
        transfer_type: str = TRANSFER_TYPE_LOCAL,
        transfer_metadata: dict | None = None,
        progress: str | None = None,
    ) -> File:
        """Upload a file to the repository.

        :param record_or_url: record or url of the record where the file will be uploaded
        :param key: key of the file
        :param file: file to upload
        :param metadata: metadata of the file
        """
        files_url = self._get_files_url(record_or_url)

        if isinstance(source, (str, Path)):
            from ..streams import FileSource

            source = FileSource(source)

        # 1. initialize the upload
        transfer_md: dict[str, Any] = {}
        transfer_payload = {"key": key, "metadata": metadata, "transfer": transfer_md}
        if transfer_type != TRANSFER_TYPE_LOCAL:
            transfer_md["type"] = transfer_type

        if transfer_metadata:
            transfer_md.update(transfer_metadata)

        from .transfer import transfer_registry

        transfer = transfer_registry.get(transfer_type)

        await transfer.prepare(self._connection, files_url, transfer_payload, source)

        with current_progress.short_task():
            initialized_upload: FilesList = await self._connection.post(
                url=files_url,
                json=[transfer_payload],
                result_class=FilesList,
            )

        initialized_upload_metadata = initialized_upload[key]

        # 2. upload the file using one of the transfer types
        if progress:
            progress_bar = current_progress.start_long_task(progress)
        else:
            progress_bar = DummyProgressBar()
        progress_bar.set_total(await source.size())
        try:
            await transfer.upload(
                self._connection, initialized_upload_metadata, source, progress_bar
            )
        finally:
            progress_bar.finish()

        # 3. prepare the commit payload
        commit_payload = await transfer.get_commit_payload(initialized_upload_metadata)

        with current_progress.short_task():
            if initialized_upload_metadata.links.commit:
                committed_upload = await self._connection.post(
                    url=initialized_upload_metadata.links.commit,
                    json=commit_payload,
                    result_class=File,
                )

                return committed_upload
            else:
                return initialized_upload_metadata

    @override
    @overload
    async def download(
        self,
        record: Record,
        key: str,
        sink: DataSink,
        *,
        parts: int | None = None,
        part_size: int | None = None,
        progress: str | None = None,
    ) -> None: ...

    @override
    @overload
    async def download(
        self,
        file_or_url: File | URL,
        sink: DataSink,
        *,
        parts: int | None = None,
        part_size: int | None = None,
        progress: str | None = None,
    ) -> None: ...

    @override  # type: ignore
    async def download(
        self,
        *args: Record | str | DataSink | File | URL,
        parts: int | None = None,
        part_size: int | None = None,
        progress: str | None = None,
    ) -> None:
        """Download the file to the sink.

        :param file_rec: file to download
        :param sink: sink where to download the file
        :param parts: number of parts to download the file in
        :param part_size: size of the parts
        :param progress: progress message in progress bar
        """
        sink: DataSink
        if len(args) == 2:
            assert isinstance(
                args[0], (File, URL)
            ), "Invalid arguments - expecting a File or URL as the first argument"
            file_or_url: File | URL = args[0]
            assert isinstance(
                args[1], DataSink
            ), "Invalid arguments - expecting a DataSink as the second argument"
            sink = args[1]
        elif len(args) == 3:
            assert isinstance(
                args[0], Record
            ), "Invalid arguments - expecting a Record as the first argument when passing file key"
            record: Record = args[0]
            assert isinstance(
                args[1], str
            ), "Invalid arguments - expecting a string key as the second argument"
            key: str = args[1]
            assert isinstance(
                args[2], DataSink
            ), "Invalid arguments - expecting a DataSink as the third argument"
            sink = args[2]
            file_or_url = await self.read(record, key)
        else:
            raise ValueError(
                "Invalid arguments - expecting either (File, DataSink), (FileURL, DataSink) or (Record, key, DataSink)"
            )

        if not isinstance(file_or_url, File):
            file_or_url = await self.read(file_or_url)

        content_url = file_or_url.links.content
        if not content_url:
            raise ValueError("The file does not have a content link")

        if progress:
            progress_bar = current_progress.start_long_task(progress)
        else:
            progress_bar = DummyProgressBar()

        await self._connection.download_file(
            content_url, sink, parts, part_size, progress_bar
        )

    def _get_files_url(self, record_or_url: Record | URL) -> URL:
        """Get the files url from the record or url."""
        if isinstance(record_or_url, Record):
            if not record_or_url.links.files:
                raise ValueError("The record does not have a files link, probably files are not enabled on it")
            return record_or_url.links.files
        return record_or_url

    @overload
    async def delete(self, record: Record, key: str | None = None) -> None: ...

    @overload
    async def delete(self, file: File) -> None: ...

    @overload
    async def delete(self, file: URL) -> None: ...

    async def delete(  # type: ignore
        self,
        arg: Record | File | URL,
        key: str | None = None,
    ) -> None:
        """Delete a record inside the repository.

        Params:
          - record and key
          - File object
          - URL of the file
        """
        if isinstance(arg, Record):
            files_url = arg.links.files
            if files_url is None:
                raise ValueError("The record does not have a files link")
            if key is None:
                raise ValueError("The key of the file to delete must be provided")
            file_url = files_url / key
        elif isinstance(arg, File):
            file_url = arg.links.self_
        else:
            file_url = arg

        await self._connection.delete(url=file_url)
