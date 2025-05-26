"""Async client for NRP repositories."""
# TODO: can not do from __future__ import annotations here
# as it is not compatible with attrs trying to resolve the
# type annotations in runtime

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, Self, overload

from yarl import URL

from ..config import RepositoryConfig
from ..types.files import TRANSFER_TYPE_LOCAL, File
from ..types.info import RepositoryInfo
from ..types.records import Record, RecordId, RecordList
from ..types.requests import Request, RequestList, RequestType, RequestTypeList
from .streams import DataSink, DataSource


class RecordStatus(Enum):
    """Selector for records."""

    ALL = "all"
    """All records"""

    PUBLISHED = "published"
    """Published records"""

    DRAFT = "draft"
    """Draft records"""


class AsyncRecordsClient(Protocol):
    """Client class for access to records."""

    def with_model(self, model: str) -> Self:
        """Return a new client limited to the given model."""
        ...

    @property
    def published_records(self) -> Self:
        """Return a new client limited to published records."""
        ...

    @property
    def draft_records(self) -> Self:
        """Return a new client limited to draft records."""
        ...

    async def create(
        self,
        data: dict[str, Any],
        *,
        model: str | None = None,
        community: str | None = None,
        workflow: str | None = None,
        idempotent: bool = False,
        files_enabled: bool = True,
    ) -> Record:
        """Create a new record in the repository.

        :param data:            the metadata of the record
        :param community:       community in which the record should be created
        :param workflow:        the workflow to use for the record, if not provided
                                the default workflow of the community is used
        :param idempotent:      if True, the operation is idempotent and can be retried on network errors.
                                Use only if you know that the operation is idempotent, for example that
                                you use PID generator that takes the persistent identifier from the data.
        :return:                the created record
        """
        ...

    async def read(
        self,
        record_id: RecordId,
        *,
        model: str | None = None,
        status: RecordStatus | None = None,
        query: dict[str, str] | None = None,
    ) -> Record:
        """Read a record from the repository. Please provide either record_id or record_url, not both.

        :param record_id:       the id of the record. Could be either pid or url
        :param model:           optional model of the record
        :param query:           extra arguments to read, repository specific
        :return:                the record
        """
        ...

    async def update(self, record: Record, *, verify_version: bool = True) -> Record:
        """Update a record in the repository.

        The record must have an id and optionally
        an etag. If the etag is not provided, the record is updated without checking
        the etag. If the etag is provided, the record is updated only if the etag matches
        the current etag of the record in the repository.

        An updated version, as stored in the repository, is returned.

        :param record: record that will be stored to the server
        :param verify_version: if set to true, verify that the record
                               on the server has not been modified in the meantime
        """
        ...

    async def delete(
        self,
        record_id_or_record: RecordId | Record,
        *,
        etag: str | None = None,
        status: RecordStatus | None = None,
    ) -> None:
        """Delete a record inside the repository.

        :param record_id: identification of the record. If record_id is passed, you can
                          specify the etag as well
        :param record: record downloaded from the repository
        :param etag: if record_id is specified, delete the record only if the version matches
        """
        ...

    async def search(
        self,
        *,
        q: Optional[str] = None,
        page: Optional[int] = None,
        size: Optional[int] = None,
        sort: Optional[str] = None,
        model: str | None = None,
        status: RecordStatus | None = None,
        facets: dict[str, str] | None = None,
    ) -> RecordList:
        """Search for records in the repository."""
        ...

    async def next_page(self, *, record_list: RecordList) -> RecordList:
        """Get the next page of records."""
        ...

    async def previous_page(self, *, record_list: RecordList) -> RecordList:
        """Get the previous page of records."""
        ...

    def scan(
        self,
        *,
        q: Optional[str] = None,
        model: str | None = None,
        status: RecordStatus | None = None,
        facets: dict[str, str] | None = None,
    ) -> AbstractAsyncContextManager[AsyncIterator[Record]]:
        """Scan all the records in the repository.

        Tries to return all matched records in a consistent manner
        (using snapshots if they are available), but this behaviour is not guaranteed.

        The implementation might rely on specific sorting, so you should not modify it
        unless you know what you are doing.

        Usage:

        ```
        async with client.scan(...) as records:
            async for record in records:
                print(record)
        ```

        Note: the with section is required so that we can clean up the resources
        if there is a break in the iteration.
        """
        ...

    async def publish(self, record: Record) -> Record | Request:
        """Publish a record.

        :param record: record to publish
        """
        pass

    async def edit_metadata(self, record: Record) -> Record | Request:
        """Edit metadata of a published record.

        :param record: published record for which metadata will be edited
        """
        pass

    async def new_version(self, record: Record) -> Record | Request:
        """Create a new version of a published record.

        :param record: published record for which the new version will be created
        """
        pass

    async def retract_published(self, record: Record) -> Record | Request:
        """Retract a published record.

        :param record: published record which will be retracted
        """
        pass
class AsyncFilesClient(Protocol):
    """Client class for accessing files stored with repository records."""

    async def list(
        self,
        record_or_url: Record | URL,
    ) -> list[File]:
        """List the files of a record."""
        ...

    @overload
    async def read(self, file_url: URL) -> File: ...

    @overload
    async def read(self, record: Record, key: str) -> File: ...

    @overload
    async def read(self, record_url: URL, key: str) -> File: ...

    async def read(  # type: ignore
        self,
        *args: Record | URL | str,
    ):
        """Read file metadata from the repository.

        You can pass either the file url directly, or the record
        (as a retrieved record or its url) and the key of the file.

        :param file_url: url of the file
        :param record: record where the file is stored
        :param record_url: url of the record where the file is stored
        :param key: key of the file
        """
        ...

    async def upload(
        self,
        record_or_url: Record | URL,
        key: str,
        metadata: dict[str, Any],
        source: DataSource | str | Path,
        transfer_type: str = TRANSFER_TYPE_LOCAL,
        transfer_metadata: dict[str, Any] | None = None,
        progress: str | None = None,
    ) -> File:
        """Upload a file to the repository.

        :param record_or_url: record or url of the record where the file will be uploaded
        :param key: key of the file
        :param file: file to upload
        :param metadata: metadata of the file
        :param progress: if set, show subprogress with this name
        """
        ...

    @overload
    async def download(
        self,
        record: Record,
        key: str,
        sink: DataSink,
        *,
        parts: int | None = None,
        part_size: int | None = None,
        progress: str | None,
    ) -> None: ...

    @overload
    async def download(
        self,
        file_or_url: File | URL,
        sink: DataSink,
        *,
        parts: int | None = None,
        part_size: int | None = None,
        progress: str | None,
    ) -> None: ...

    async def download(  # type: ignore
        self,
        *args: Record | str | DataSink | File | URL,
        parts: int | None = None,
        part_size: int | None = None,
        progress: str | None,
    ) -> None:
        """Download the file to the sink.

        :param file_rec: file to download
        :param sink: sink where to download the file
        :param parts: number of parts to download the file in
        :param part_size: size of the parts
        :param progress: if set, show subprogress with this name
        """
        ...

    async def update(self, file: File) -> File:
        """Update the file metadata in the repository.

        :param file: file to update
        """
        ...

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
        ...

class AsyncRequestsClient(Protocol):
    """An abstract client for requests within the NRP repository.

    A request is an operation initiated by the user on a topic.
    It can be a request to publish a record, to delete a record,
    assign a DOI, etc. The request has a recipient (which is determined
    automatically by the server) and a status (which can be created,
    accepted, rejected, cancelled, ...).

    After the request is created, the user can check the status of the request
    and wait until the request is completed. Completion of a request might
    trigger automatic action, like publishing a record or assigning a DOI.
    """

    async def applicable_requests(
        self, topic: Record | URL, params: dict[str, str] | None = None
    ) -> RequestTypeList:
        """Return all requests that can be created on a given topic at this moment."""
        ...

    @overload
    async def create(
        self,
        type_: RequestType,
        payload: dict[str, Any],
        submit: bool = False,
    ) -> Request: ...

    @overload
    async def create(
        self,
        topic: Record | URL,
        type_: str,
        payload: dict[str, Any],
        submit: bool = False,
    ) -> Request: ...

    async def create(  # type: ignore
        self,
        *args: Record | URL | RequestType | str | dict[str, Any],
        submit: bool = False,
    ) -> Request:
        """Create a new request of this type."""
        ...

    async def all(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Search for all requests the user has access to.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def created(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all requests, that are created but not yet submitted.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def submitted(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all submitted requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def accepted(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all accepted requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def declined(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all declined requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def expired(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all expired requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def cancelled(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all cancelled requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def read_request(self, request_id: str) -> Request:
        """Read a single request by its id.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        ...

    async def submit(
        self, request: Request | URL, payload: dict[str, Any] | None = None
    ) -> Request:
        """Submit the request.

        The request will be either passed to receivers, or auto-approved
        depending on the current workflow
        """
        ...

    async def accept(
        self, request: Request | URL, payload: dict[str, Any] | None = None
    ) -> Request:
        """Accept the submitted request."""
        ...

    async def decline(
        self, request: Request | URL, payload: dict[str, Any] | None = None
    ) -> Request:
        """Decline the submitted request."""
        ...

    async def cancel(
        self, request: Request | URL, payload: dict[str, Any] | None = None
    ) -> Request:
        """Cancel the request."""
        ...


class AsyncRepositoryClient(Protocol):
    """An abstract client for NRP repositories.

    Usually, subclasses of this class are not instantiated directly in your code.
    To get an instance of a repository, use the high-level method `get_async_client`:

    ```
    my_client = await async_client(config?, url=url, refresh=False/True)
    my_client = await async_client(config?, alias=alias, refresh=False/True)
    ```

    and then use the instance.
    """

    # region info endpoint
    @classmethod
    async def can_handle_repository(
        cls, url: URL | str, verify_tls: bool = True
    ) -> URL | None:
        """Return if this client can handle a repository that contains the passed URL.

        This method can make an http request or use any means to check if the repository
        at the URL can be handled by this client.

        :param url: any url within the repository (root, record api, html, documentation
        if running on the same host, ...)
        :param verify_tls: whether to verify tls (should be switched on for production)
        :return: API url of the server or None if this client can not handle the repository
        """
        ...

    @classmethod
    async def from_configuration(
        cls,
        config: RepositoryConfig,
        refresh: bool = False,
        extra_tokens: dict[URL, str] | None = None,
    ) -> Self:
        """Create a client from the given configuration.

        :param config: the configuration for the repository
        :param refresh: refresh the configuration by calling get_repository_info
        """
        ...

    async def get_repository_info(self, refresh: bool = True) -> RepositoryInfo:
        """Get information about the repository.

        This call is cached inside the RepositoryConfig instance.

        :param refresh: refresh the info from the server
        """
        ...

    # endregion

    @property
    def records(self) -> AsyncRecordsClient:
        """Return client for accessing records."""
        ...

    @property
    def files(self) -> AsyncFilesClient:
        """Return client for accessing files."""
        ...

    @property
    def requests(self) -> AsyncRequestsClient:
        """Return the requests session used by the client."""
        ...

    @property
    def config(self) -> RepositoryConfig:
        """Return the configuration of the repository."""
        ...
