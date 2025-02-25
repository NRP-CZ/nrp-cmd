from typing import Any, cast, overload, override

from yarl import URL

from ...types.info import RepositoryInfo
from ...types.records import Record
from ...types.requests import (
    Request,
    RequestList,
    RequestStatus,
    RequestType,
    RequestTypeList,
)
from ..base_client import AsyncRequestsClient
from ..connection import AsyncConnection


class AsyncInvenioRequestsClient(AsyncRequestsClient):
    """Invenio requests client implementation."""

    def __init__(self, connection: AsyncConnection, info: RepositoryInfo):
        """Initialize the client."""
        self._connection = connection
        self._info = info

    @override
    async def applicable_requests(
        self, topic: Record | URL, params: dict[str, str] | None = None
    ) -> RequestTypeList:
        """Return all requests that can be created on a given topic at this moment."""
        topic_url: URL
        if isinstance(topic, Record):
            if not topic.links.files:
                raise ValueError(
                    "The record does not have a files link, probably files are not enabled on it"
                )
            topic_url = topic.links.applicable_requests
        else:
            topic_url = topic / "applicable-requests"

        return await self._connection.get(
            url=topic_url,
            result_class=RequestTypeList,
            params=params or {},
        )

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

        if len(args) == 2:
            type_ = cast(RequestType, args[0])
            payload = cast(dict[str, Any], args[1])
            assert isinstance(
                type_, RequestType
            ), "Invalid argument - expecting a request type"
        elif len(args) == 3:
            topic = cast(Record | URL, args[0])
            type_name = cast(str, args[1])
            payload = cast(dict[str, Any], args[2])
            request_types = await self.applicable_requests(topic)
            type_ = request_types[type_name]
        else:
            raise ValueError("Invalid arguments")

        if not type_.links.actions.create:
            raise ValueError(f"The request type {type_.id} does not support creation")
        request: Request = await self._connection.post(
            url=type_.links.actions.create,
            json=payload,
            result_class=Request,
        )
        if submit:
            return await self.submit(request)
        return request

    @override
    async def all(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Search for all requests the user has access to.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        requests_url: URL

        if topic is not None:
            if isinstance(topic, Record):
                requests_url = topic.links.requests
            elif isinstance(topic, URL):
                requests_url = topic / "requests"
            else:
                raise ValueError("Invalid topic")
        else:
            if not self._info.links.requests:
                raise ValueError("The repository does not have a requests link")
            requests_url = self._info.links.requests

        return await self._connection.get(
            url=requests_url,
            result_class=RequestList,
            params=params or {},
        )

    @override
    async def created(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all requests, that are created but not yet submitted.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        return await self.all(
            topic=topic, params={**(params or {}), "status": "created"}
        )

    @override
    async def submitted(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all submitted requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        return await self.all(
            topic=topic, params={**(params or {}), "status": "submitted"}
        )

    @override
    async def accepted(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all accepted requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        return await self.all(
            topic=topic, params={**(params or {}), "status": "accepted"}
        )

    @override
    async def declined(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all declined requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        return await self.all(
            topic=topic, params={**(params or {}), "status": "declined"}
        )

    @override
    async def expired(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all expired requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        return await self.all(
            topic=topic, params={**(params or {}), "status": "expired"}
        )

    @override
    async def cancelled(
        self, *, topic: Record | URL | None = None, params: dict[str, str] | None = None
    ) -> RequestList:
        """Return all cancelled requests.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        return await self.all(
            topic=topic, params={**(params or {}), "status": "cancelled"}
        )

    @override
    async def read_request(self, request_id: str) -> Request:
        """Read a single request by its id.

        :param topic:  if given, filter the requests by the topic
        :param params: Additional parameters to pass to the search query, see repository docs for possible values
        """
        if self._info.links.requests is None:
            raise ValueError("The repository does not have a requests link")

        return await self._connection.get(
            url=self._info.links.requests / request_id,
            result_class=Request,
        )

    @override
    async def submit(
        self, request: Request | URL, payload: dict | None = None
    ) -> Request:
        """Submit the request.

        The request will be either passed to receivers, or auto-approved
        depending on the current workflow
        """
        return await self._push_request(
            request=request,
            required_request_status=RequestStatus.CREATED,
            action="submit",
            payload=payload,
        )

    @override
    async def accept(
        self, request: Request | URL, payload: dict | None = None
    ) -> Request:
        """Accept the submitted request."""
        return await self._push_request(
            request=request,
            required_request_status=RequestStatus.SUBMITTED,
            action="accept",
            payload=payload,
        )

    @override
    async def decline(
        self, request: Request | URL, payload: dict | None = None
    ) -> Request:
        """Decline the submitted request."""
        return await self._push_request(
            request=request,
            required_request_status=RequestStatus.SUBMITTED,
            action="decline",
            payload=payload,
        )

    @override
    async def cancel(
        self, request: Request | URL, payload: dict | None = None
    ) -> Request:
        """Cancel the request."""
        return await self._push_request(
            request=request,
            required_request_status=RequestStatus.CREATED,
            action="cancel",
            payload=payload,
        )

    async def _push_request(
        self,
        *,
        request: Request | URL,
        required_request_status: str,
        action: str,
        payload: dict | None,
    ) -> Request:
        """Push the request to the server."""
        if isinstance(request, URL):
            request = await self._connection.get(
                url=request,
                result_class=Request,
            )

        if request.status != required_request_status:
            raise ValueError(
                f"Can {action} only requests with status {required_request_status}, not {request.status}"
            )

        action_link = getattr(request.links.actions, action)

        if not action_link:
            raise ValueError(f"You have no permission to {action} this request")

        return await self._connection.post(
            url=action_link, json=payload or {}, result_class=Request
        )
