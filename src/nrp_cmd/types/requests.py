"""Types for requests in the NRP repository."""

from datetime import datetime
from enum import StrEnum, auto
from typing import Any, Optional

from attrs import define, field
from cattrs.dispatch import StructureHook
from yarl import URL

from ..converter import Omit, Rename, WrapStructure, extend_serialization
from .base import Model
from .records import BaseRecord
from .rest import RESTList, RESTObject, RESTObjectLinks

# region request types

@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class RequestTypeActionLinks(Model):
    """Links on a request type object."""

    create: Optional[URL] = None
    """Link to create a new request of this type."""


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class RequestTypeLinks(Model):
    """Links on a request type."""

    actions: RequestTypeActionLinks = field()
    """Actions that can be performed on the request type."""


@extend_serialization(Omit("_etag", from_unstructure=True), 
                      allow_extra_data=True)
@define(kw_only=True)
class RequestType(RESTObject):
    """A type of request that the user can apply for.

    An example might be a request for access to a dataset,
    publish draft request, assign doi request, ...
    """

    type_id: str = field()
    """Unique identifier of the request type."""

    links: RequestTypeLinks = field()
    """Links on the request type object."""


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class RequestTypeList(RESTList[RequestType]):
    """A list of request types as returned from the API."""

    def __getitem__(self, type_id: str) -> RequestType:
        """Return a request type by its type_id.

        :param type_id:     type_id, stays stable regardless of server version
        :return:            request type or None if not found
        """
        for hit in self.hits:
            if hit.type_id == type_id:
                return hit
        raise KeyError(f"Request type {type_id} not found")

    def __contains__(self, type_id: str) -> bool:
        """Check if a request type with the given type_id is in the list.

        :param type_id:     type_id, stays stable regardless of server version
        :return:            True if the request type is in the list
        """
        return type_id in self.keys()

    def keys(self) -> set[str]:
        """Return all type_ids of the request types in this list.

        :return: a set of type_ids
        """
        return {hit.type_id for hit in self.hits}

    def __getattr__(self, type_id: str) -> RequestType:
        """Return a request type by its type_id.

        Shortcut to be able to write request_types.publish_draft instead of request_types["publish_draft"]
        """
        if type_id in self.keys():
            return self[type_id]
        return super().__getattr__(type_id)

# endregion

# region requests


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class RequestActionLinks(Model):
    """Possible actions on a request."""

    submit: Optional[URL] = None
    cancel: Optional[URL] = None
    accept: Optional[URL] = None
    decline: Optional[URL] = None


@extend_serialization(Rename("self", "self_"), allow_extra_data=True)
@define(kw_only=True)
class RequestLinks(RESTObjectLinks):
    """Links on a request."""

    actions: RequestActionLinks = field()
    """Actions that can be performed on the request at the moment by the current user."""

    comments: URL = field()
    """Link to the comments on the request"""

    timeline: URL = field()
    """Link to the timeline (events) of the request"""


class RequestStatus(StrEnum):
    """Status of the request."""

    CREATED = auto()
    ACCEPTED = auto()
    DECLINED = auto()
    SUBMITTED = auto()
    CANCELLED = auto()
    EXPIRED = auto()


@define(kw_only=True)
class RequestPayloadRecord(Model):
    """A publish/edit/new version request can have a simplified record serialization inside its payload.

    Currently the serialization contains only links to the published/draft record.
    """

    links: RESTObjectLinks
    """Links to the record (self and self_html)"""


def restore_hierarchy(data: dict[str, Any], type_: type, previous: StructureHook) -> Any: # noqa: ANN401
    """Restore the hierarchy of the request payload."""

    def _parse_colon_hierarchy(obj: dict[str, Any], key: str, value: Any) -> None:   # noqa: ANN401
        parts = key.split(":")
        for part in parts[:-1]:
            obj = obj.setdefault(part, {})
        obj[parts[-1]] = value

    if not data:
        return previous(data, type_)
    
    obj: dict[str, Any] = {}
    for k, v in data.items():
        _parse_colon_hierarchy(obj, k, v)
    return previous(obj, type_)

@extend_serialization(WrapStructure(restore_hierarchy), allow_extra_data=True)
@define(kw_only=True)
class RequestPayload(Model):
    """Payload of a request.

    It can be of different types, depending on the request type.
    In the library, the payload is extensible. If you know that there is a specific property
    on the payload, just use payload.property_name to access it.
    """

    published_record: RequestPayloadRecord | None = None
    """A publish request can have a simplified record serialization inside its payload."""

    draft_record: RequestPayloadRecord | None = None
    """An edit request can have a simplified record serialization inside its payload."""


@extend_serialization(allow_extra_data=False)
@define(kw_only=True)
class Request(BaseRecord):
    """Interface for a request in the NRP repository."""

    links: RequestLinks = field()
    """Links on the request object."""

    type: str = field()
    """Request type identifier."""

    title: Optional[str] = None
    """Title of the request, might be None"""

    status: RequestStatus = field()
    """Status of the request"""

    is_closed: bool = field()
    """Is the request closed?"""

    is_open: bool = field()
    """Is the request open?"""

    expires_at: Optional[datetime] = None
    """When the request expires, might be unset"""

    is_expired: bool = field()
    """Is the request expired?"""

    created_by: dict[str, str] = field()
    """Who created the request. It is a dictionary containing a 
    reference to the creator (NOT the links at the moment)."""

    receiver: dict[str, str] = field()
    """Who is the receiver of the request. It is a dictionary containing a 
    reference to the receiver (NOT the links at the moment)."""

    topic: dict[str, str] = field()
    """The topic of the request. It is a dictionary containing a
    reference to the topic (NOT the links at the moment)."""

    payload: Optional[RequestPayload] = None
    """Payload of the request. It can be of different types, depending on the request type."""

    def __attrs_post_init__(self):
        """Check that the created_by, receiver and topic are single values."""
        single_value_expected(self.created_by)
        single_value_expected(self.receiver)
        single_value_expected(self.topic)


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class RequestList(RESTList[Request]):
    """A list of requests."""

    sortBy: Optional[str] = None
    """By which property should be the list sorted"""

    aggregations: Optional[Any] = None
    """Aggregations of the list"""



def single_value_expected(value: list[Any] | tuple[Any, ...] | dict[Any, Any]) -> None:
    """Check that the value is a single value."""
    assert len(value) == 1, "Expected exactly one value"
