from __future__ import annotations

import contextlib
import copy
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, Optional, Self, override

from yarl import URL

from ...converter import converter
from ...types.info import RepositoryInfo
from ...types.records import Record, RecordId, RecordList
from ...types.requests import Request, RequestType
from ...types.rest import RESTHits, RESTPaginationLinks
from ..base_client import AsyncRecordsClient, RecordStatus
from ..connection import AsyncConnection
from .requests import AsyncInvenioRequestsClient

OPENSEARCH_SCAN_WINDOW = 5000
OPENSEARCH_SCAN_PAGE = 100


class AsyncInvenioRecordsClient(AsyncRecordsClient):
    def __init__(
        self,
        connection: AsyncConnection,
        info: RepositoryInfo,
        requests_client: AsyncInvenioRequestsClient,
    ):
        """Initialize the client."""
        self._connection = connection
        self._info = info
        self._model: str | None = None
        self._status: RecordStatus = RecordStatus.ALL
        self._requests_client = requests_client

    @override
    def with_model(self, model: str) -> Self:
        """Return a new client limited to the given model."""
        ret = copy.copy(self)
        ret._model = model
        return ret

    @override
    @property
    def published_records(self) -> Self:
        """Return a new client limited to published records."""
        ret = copy.copy(self)
        ret._status = RecordStatus.PUBLISHED
        return ret

    @override
    @property
    def draft_records(self) -> Self:
        """Return a new client limited to draft records."""
        ret = copy.copy(self)
        ret._status = RecordStatus.DRAFT
        return ret

    @override
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
        if idempotent:
            raise NotImplementedError("Idempotent for create not implemented yet")

        # if model is not provided, try to use currently set model
        model = model or self._model

        # if there is no model, try to estimate it by $schema in the data
        if not model and "$schema" in data:
            model_schema = data["$schema"]
            for model_info in self._info.models.values():
                if model_info.schema == model_schema:
                    model = model_info.type
                    data.pop("$schema")
                    break

        # if there is still no model, try to use repository's default model
        if not model and self._info.default_model:
            model = self._info.default_model

        # if we still do not have the model, just use repository's url and let it decide
        if not model:
            create_url = self._info.links.records
            has_metadata = False
        else:
            # take the deposit url from the model
            create_url = self._info.models[model].links.records
            has_metadata = self._info.models[model].metadata

        if has_metadata and "metadata" not in data:
            data = {"metadata": {**data}}
        else:
            data = {**data}

        if community or workflow:
            parent: dict[str, Any] = (
                copy.deepcopy(data.pop("parent")) if "parent" in data else {}
            )
            data["parent"] = parent
            if community:
                assert (
                    "community" not in parent
                ), f"Community already in parent: {parent}"
                parent["communities"] = {"default": community}
            if workflow:
                assert "workflow" not in parent, f"Workflow already in data: {parent}"
                parent["workflow"] = workflow
        data["files"] = {"enabled": files_enabled}

        return await self._connection.post(
            url=create_url,
            json=data,
            idempotent=idempotent,
            result_class=Record,
        )

    @override
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
        :return:                the record
        """
        record_url = _record_id_to_url(
            self._info, record_id, model or self._model, status or self._status
        )

        if query:
            record_url = record_url.with_query(**query)
        return await self._connection.get(
            url=record_url,
            result_class=Record,
        )

    @override
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
        search_url, extra_facets = _get_search_params(self._info, model or self._model, status or self._status)

        query = {**(facets or {}), **extra_facets}
        if q:
            query["q"] = q
        if page is not None:
            query["page"] = str(page)
        if size is not None:
            query["size"] = str(size)
        if sort:
            query["sort"] = sort

        return await self._connection.get(
            url=search_url,
            params=query,
            result_class=RecordList,
        )

    @override
    async def next_page(self, *, record_list: RecordList) -> RecordList:
        """Get the next page of records."""
        next_url = record_list.links.next
        if next_url:
            return await self._connection.get(
                url=next_url,
                result_class=RecordList,
            )
        else:
            return self._empty_record_list()

    def _empty_record_list(self):
        return RecordList(
            links=RESTPaginationLinks(
                self_=None,     # type: ignore
            ),
            hits=RESTHits[Record](total=0, hits=[]),
        )

    @override
    async def previous_page(self, *, record_list: RecordList) -> RecordList:
        """Get the previous page of records."""
        prev_url = record_list.links.prev
        if prev_url:
            return await self._connection.get(
                url=prev_url,
                result_class=RecordList,
            )
        else:
            return self._empty_record_list()

    @override
    @contextlib.asynccontextmanager
    async def scan(  # type: ignore
        self,  #  - as we can not find working mypy type tht would work with parent class
        *,
        q: Optional[str] = None,
        model: str | None = None,
        status: RecordStatus | None = None,
        facets: dict[str, str] | None = None,
    ) -> AsyncGenerator[AsyncIterator[Record], None]:
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

        Note: in invenio, we do not have the scan api over the rest, so we simulate it
        by:
            * searching page by page if the number of records < OPENSEARCH_SCAN_WINDOW
            * scanning by date bisection if the number of records > OPENSEARCH_SCAN_WINDOW
        """

        def opensearch_date_serialize(date: datetime) -> str:
            return date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        def opensearch_date_interval(start: datetime, end: datetime) -> str:
            return f"[{opensearch_date_serialize(start)} TO {opensearch_date_serialize(end)}{'}'}"

        async def paginated_scan(
            q: str | None,
            model: str | None,
            status: RecordStatus | None,
            facets: dict[str, str] | None = None,
        ) -> AsyncIterator[Record]:
            result = await self.search(
                q=q,
                size=OPENSEARCH_SCAN_PAGE,
                model=model,
                status=status,
                facets=facets,
            )
            while result.hits.hits:
                for record in result.hits.hits:
                    yield record
                result = await self.next_page(record_list=result)

        async def scan_via_date_bisect() -> AsyncIterator[Record]:
            result = await self.search(q=q, size=1, facets=dict(sort="oldest"))
            first_created = result.hits.hits[0].created
            result = await self.search(q=q, size=1, facets=dict(sort="newest"))
            last_created = result.hits.hits[0].created

            # make sure that the first_created and last_created are in UTC
            first_created = first_created.astimezone(UTC) - timedelta(seconds=1)
            last_created = last_created.astimezone(UTC) + timedelta(seconds=1)

            # reversed to push the first half at the top
            stack = [
                [date_in_between(first_created, last_created), last_created],
                [first_created, date_in_between(first_created, last_created)],
            ]

            while stack:
                start, end = stack.pop()
                date_query = f"created:{opensearch_date_interval(start, end)}"
                if q:
                    subquery = f"({q}) AND {date_query}"
                else:
                    subquery = date_query
                result = await self.search(
                    q=subquery,
                    size=1,
                    model=model,
                    status=status,
                    facets=facets,
                )

                if result.hits.total <= OPENSEARCH_SCAN_WINDOW:
                    if result.hits.total:
                        async for record in paginated_scan(
                            q=subquery,
                            model=model,
                            status=status,
                            facets=facets,
                        ):
                            yield record
                else:
                    # reversed to push the first half at the top
                    stack.append([date_in_between(start, end), end])
                    stack.append([start, date_in_between(start, end)])

        async def _scan_pages() -> AsyncGenerator[Record, None]:
            # at first check if we can get all records in one paginated listing
            # repository can not handle page_size=0, so we use 1
            result = await self.search(
                q=q,
                size=1,
                model=model,
                status=status,
                facets=facets,
            )
            if result.hits.total <= OPENSEARCH_SCAN_WINDOW:
                if result.hits.total:
                    async for record in paginated_scan(q, model, status, facets):
                        yield record
            else:
                # there is more than OPENSEARCH_SCAN_WINDOW records, that means
                # that we do not know even the result count. We will get to it
                # by scanning the records by date and using bisection.
                async for record in scan_via_date_bisect():
                    yield record

        yield _scan_pages()

    def _etag_headers(self, etag: str | None) -> dict[str, str]:
        """Return the headers with the etag if it was returned by the repository."""
        headers: dict[str, str] = {}
        if etag:
            headers["If-Match"] = etag
        return headers

    @override
    async def update(self, record: Record, *, verify_version: bool = True) -> Record:
        """Update a record in the repository.

        The record must have an id and optionally
        an etag. If the etag is not provided, the record is updated without checking
        the etag. If the etag is provided, the record is updated only if the etag matches
        the current etag of the record in the repository.

        An updated version, as stored in the repository, is returned.

        :param record: record that will be stored to the server
        """
        headers: dict[str, str] = {}
        if verify_version:
            headers.update(self._etag_headers(record.get_etag()))

        ret = await self._connection.put(
            url=record.links.self_,
            json=converter.unstructure(record),  # type: ignore
            headers={
                **headers,
                "Content-Type": "application/json",
            },
            result_class=Record,
        )
        return ret

    @override
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
        if isinstance(record_id_or_record, Record):
            url = record_id_or_record.links.self_
            etag = record_id_or_record._etag    # type: ignore
        else:
            url = _record_id_to_url(self._info, record_id_or_record, self._model, 
                                   status=status or self._status)

        return await self._connection.delete(url=url, headers=self._etag_headers(etag))

    async def publish(self, record: Record) -> Record | Request:
        """Publish a record.

        :param record: record to publish
        """
        return await self._request_op(
            record,
            "publish_draft",
            "publish",
            "post",
            "Can not publish a record",
        )

    async def _request_op(
        self,
        record: Record,
        request_type_id: str,
        link_name: str,
        link_op: str,
        error_msg: str,
    ) -> Record | Request:
        if record.links["applicable-requests"]:
            request_types = await self._requests_client.applicable_requests(record)

            request_type: RequestType | None = next(
                (rt for rt in request_types.hits if rt.type_id == request_type_id), None
            )
            if not request_type:
                raise ValueError(
                    f"{error_msg}: Request type {request_type_id} not found "
                    f"in applicable requests on {record.id}. Run list requests operation "
                    "to get the list of available requests."
                )

            request = await self._requests_client.create(request_type, {}, submit=True)
            if request.status == "accepted":
                return await self.read(request.links.topic)
            return request
        else:
            return await getattr(self._connection, link_op)(
                url=getattr(record.links, link_name),
                json={},
                result_class=Record,
            )

    async def edit_metadata(self, record: Record) -> Record | Request:
        """Edit metadata of a published record.

        :param record: published record for which metadata will be edited
        """
        return await self._request_op(
            record,
            "edit_published_record",
            "draft",
            "post",
            "Can not edit metadata of a record",
        )

    async def new_version(self, record: Record) -> Record | Request:
        """Edit metadata of a published record.

        :param record: published record for which metadata will be edited
        """
        return await self._request_op(
            record,
            "new_version",
            "versions",
            "post",
            "Can not create a new version of a record",
        )

    async def retract_published(self, record: Record) -> Record | Request:
        """Edit metadata of a published record.

        :param record: published record for which metadata will be edited
        """
        return await self._request_op(
            record,
            "delete_published_record",
            "self_",
            "delete",
            "Can not retract a record",
        )

def date_in_between(date1: datetime, date2: datetime):
    return date1 + (date2 - date1) / 2


def _record_id_to_url(
    info: RepositoryInfo, record_id: RecordId, model: str | None, status: RecordStatus
) -> URL:
    if isinstance(record_id, URL):
        return record_id
    if isinstance(record_id, str) and record_id.startswith("https://"):
        return URL(record_id)
    if model is None and info.default_model:
        model = info.default_model
    if model is None or model == "*":
        base_url = info.links.records
    else:
        base_url = info.models[model].links.records
    ret = base_url / str(record_id)
    if status == RecordStatus.DRAFT:
        ret /= "draft"
    return ret

def _get_search_params(
    info: RepositoryInfo, model: str | None, status: RecordStatus
) -> tuple[URL,dict[str, str]]:
    if model is None and info.default_model:
        model = info.default_model
    if model is None or model == "*":
        if status == RecordStatus.DRAFT:
            draft_url = info.links.drafts
            if draft_url is None:
                raise ValueError("Repository does not support drafts on a generic url")
            return draft_url, {
                "is_published": "false",
            }
        else:
            return info.links.records, {}

    if status == RecordStatus.DRAFT:
        draft_url = info.models[model].links.drafts
        if draft_url is None:
            raise ValueError(f"Model {model} does not support drafts")
        return draft_url, {
            "is_published": "false",
        }
    return info.models[model].links.records, {}
