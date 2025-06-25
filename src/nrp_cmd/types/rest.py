#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Base rest types."""

# TODO: can not use from __future__ import annotations because of attrs
# currently python is unable to resolve type hints for generic types
# when from __future__ import annotations is used

from collections.abc import Iterator  # noqa TCH003 attrs need to have types in runtime
from datetime import datetime  # noqa TCH003 attrs need to have types in runtime
from types import UnionType
from typing import Any, Union, get_args, get_origin, TypeAliasType

from attrs import define, field
from yarl import URL  # noqa TCH003 attrs need to have types in runtime

from ..converter import Rename, converter, extend_serialization, Omit
from .base import Model


@extend_serialization(Rename("self", "self_"), allow_extra_data=True)
@define(kw_only=True)
class RESTObjectLinks(Model):
    """Each rest object must return a links section."""

    self_: URL
    """Link to the object itself (API)"""

    self_html: URL | None = None
    """Link to the object itself (HTML page if it has any)"""


@extend_serialization(Omit("_etag", from_unstructure=True), allow_extra_data=True)
@define(kw_only=True)
class RESTObject(Model):
    """Base class for all objects returned from the REST API."""

    links: RESTObjectLinks
    """Links to the object itself"""

    _etag: str | None = field(default=None, alias="etag", init=False)

    def get_etag(self) -> str | None:
        """Return the ETag of the object."""
        return self._etag


@extend_serialization(Rename("self", "self_"), allow_extra_data=True)
@define(kw_only=True)
class RESTPaginationLinks(RESTObjectLinks):
    """Extra links on the pagination response."""

    next: URL | None = None
    """Link to the next page"""

    prev: URL | None = None
    """Link to the previous page"""


@define(kw_only=True)
class RESTHits[T: RESTObject](Model):
    """List of records on the current page."""

    hits: list[T]
    """List of records"""
    
    total: int    


    def __len__(self) -> int:
        """Return the number of records on the current page."""
        return len(self.hits)

    def __iter__(self) -> Iterator[T]:
        """Iterate over the records on the current page."""
        return iter(self.hits)
    
    def __getitem__(self, index: int) -> T:
        """Return the record at the given index."""
        return self.hits[index]

# Note: extending classes need to add this to their decorator
# @extend_serialization(Omit("_etag", from_unstructure=True), allow_extra_data=True)
@define(kw_only=True)
class RESTList[T: RESTObject](RESTObject):
    """List of REST objects according to the Invenio REST API conventions."""

    links: RESTPaginationLinks = field()
    """Links to the current page, next and previous pages"""

    hits: RESTHits[T] = field(alias='hits')
    """List of records on the current page"""

    @property
    def total(self) -> int:
        """Return the total number of records."""
        return self.hits.total

    def __len__(self) -> int:
        """Return the number of records on the current page."""
        return len(self.hits)

    def __iter__(self) -> Iterator[T]:
        """Iterate over the records on the current page."""
        return iter(self.hits)

    def has_next(self) -> bool:
        """Check if there is a next page."""
        return bool(self.links.next)

    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return bool(self.links.prev)

type RecordIdType = str | int


def is_record_id(t: Any) -> bool:
    """Return true if given type is record id."""
    if isinstance(t, TypeAliasType):
        t = t.__value__
    origin = get_origin(t)
    if origin not in (UnionType, Union):
        return False
    base_types = get_args(t)
    return set(base_types) == {str, int}


converter.register_structure_hook_func(is_record_id, lambda v, ty: v)
converter.register_unstructure_hook_func(is_record_id, lambda v: v)

@extend_serialization(Omit("_etag", from_unstructure=True), allow_extra_data=True)
@define(kw_only=True)
class BaseRecord(RESTObject):
    """Interface for a record in the NRP repository."""

    id: RecordIdType = field()
    """Identifier of the record"""

    created: datetime = field()
    """Timestamp when the record was created"""

    updated: datetime = field()
    """Timestamp when the record was last updated"""

    revision_id: int | None = None
    """Internal revision identifier of the record"""
