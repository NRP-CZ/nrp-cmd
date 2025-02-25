#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Record types."""

# TODO: can not use from __future__ import annotations here because of the attrs plugin
# currently python is unable to resolve type hints for generic types
# when from __future__ import annotations is used

from typing import Any, Optional

from attrs import define, field
from yarl import URL

from ..converter import Omit, Rename, extend_serialization
from .base import Model
from .rest import BaseRecord, RESTList, RESTObjectLinks

RecordId = str | int | URL



@extend_serialization(Rename("self", "self_"), allow_extra_data=True)
@define(kw_only=True)
class RecordLinks(RESTObjectLinks):
    """Links of a record."""

    files: Optional[URL] = None


@define(kw_only=True)
class FilesEnabled(Model):
    """Files enabled marker."""

    enabled: bool


@define(kw_only=True)
class ParentRecord(Model):
    """Parent record of the record."""

    communities: dict[str, str] | None = None
    """Communities of the record."""

    workflow: str | None = None
    """Workflow of the record."""


# extend record serialization to allow extra data and rename files to files_
@extend_serialization(Rename("files", "files_"), 
                      Omit("_etag", from_unstructure=True), 
                      allow_extra_data=True)
@define(kw_only=True)
class Record(BaseRecord):
    """Record in the repository."""

    links: RecordLinks = field()
    """Links of the record."""

    files_: Optional[FilesEnabled] = None
    """Files enabled marker."""

    parent: Optional[ParentRecord] = None

    @property
    def metadata(self) -> dict[str, Any]:
        """Return the metadata of the record."""
        if 'metadata' in self._extra_data:
            return self._extra_data['metadata']
        return self._extra_data


@extend_serialization(Omit("_etag", from_unstructure=True), allow_extra_data=True)
@define(kw_only=True)
class RecordList(RESTList[Record]):
    """List of records."""

    sortBy: Optional[str] = None
    """Sort by field."""
    aggregations: Optional[Any] = None
    """Aggregations."""
