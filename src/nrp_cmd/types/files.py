#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""File types."""

# TODO: can not use from __future__ import annotations here because of the attrs plugin
# currently python is unable to resolve type hints for generic types
# when from __future__ import annotations is used

from typing import Any, Optional

from attrs import define, field
from yarl import URL

from ..converter import Omit, Rename, extend_serialization
from .base import Model
from .rest import RESTObject, RESTObjectLinks

# some of transfer types. Repository might provide additional ones.
TRANSFER_TYPE_LOCAL = "L"
TRANSFER_TYPE_MULTIPART = "M"
TRANSFER_TYPE_FETCH = "F"
TRANSFER_TYPE_REMOTE = "R"


@extend_serialization(Rename("type", "type_"), allow_extra_data=True)
@define(kw_only=True)
class FileTransfer(Model):
    """File transfer metadata."""

    type_: str = field(default=TRANSFER_TYPE_LOCAL)


@define(kw_only=True)
class MultipartUploadLinks(Model):
    """Links for multipart uploads."""

    url: URL
    """The url where to upload the part to."""


@extend_serialization(Rename("self", "self_"), allow_extra_data=True)
@define(kw_only=True)
class FileLinks(RESTObjectLinks):
    """Links for a single invenio file."""

    content: Optional[URL] = None
    """Link to the content of the file."""

    commit: Optional[URL] = None
    """Link to commit (finalize) uploading of the file."""

    parts: Optional[list[MultipartUploadLinks]] = None
    """For multipart upload, links where to upload the part to."""


@extend_serialization(Omit("_etag", from_unstructure=True), allow_extra_data=True)
@define(kw_only=True)
class File(RESTObject):
    """A file object as stored in .../files/<key>."""

    key: str
    """Key(filename) of the file."""

    metadata: dict[str, Any] | None = field(factory=dict)
    """Metadata of the file, as defined in the model."""

    links: FileLinks | None = None
    """Links to the file content and commit."""

    transfer: FileTransfer = field(
        factory=lambda: FileTransfer(type_=TRANSFER_TYPE_LOCAL)
    )
    """File transfer type and metadata."""

    status: Optional[str] = None

    size: Optional[int] = None


@extend_serialization(Omit("_etag", from_unstructure=True), allow_extra_data=True)
@define(kw_only=True)
class FilesList(RESTObject):
    """A list of files, as stored in ...<record_id>/files."""

    enabled: bool
    """Whether the files are enabled on the record."""

    entries: list[File] = field(factory=list)
    """List of files on the record."""

    def __getitem__(self, key: str) -> File:
        """Get a file by key."""
        for v in self.entries:
            if v.key == key:
                return v
        raise KeyError(f"File with key {key} not found")


class FilesAPIList(list):

    def as_dataframe(self, *keys: str):
        """Convert the list of files to a pandas DataFrame."""
        import pandas as pd

        from .records import _getter

        if not keys:
            keys = [
                "key",
                "metadata",
                "size",
                "checksum",
                "links.content",
            ]

        converted_files = []
        for _file in self:
            converted_file = {}
            for key in keys:
                converted_file[key] = _getter(_file, key.split("."))
            converted_files.append(converted_file)
        return pd.DataFrame(converted_files)
