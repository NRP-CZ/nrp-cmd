#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Repository info endpoint response types."""

from typing import Optional

from attrs import define, field
from yarl import URL

from ..converter import Rename, extend_serialization
from . import Model


@extend_serialization(Rename("self", "self_"), allow_extra_data=True)
@define(kw_only=True)
class RepositoryInfoLinks(Model):
    """Links within the repository info endpoint."""

    self_: URL = field()
    """Link to the repository itself"""

    records: URL = field()
    """Link to the global search endpoint"""

    drafts: URL | None = field(default=None)
    """Link to the user's records"""

    models: Optional[URL] = field(default=None)
    """Link to the models in the repository"""

    requests: URL | None = field(default=None)
    """Link to the requests in the repository"""


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class ModelInfoLinks(Model):
    """Links within the model info endpoint."""

    records: URL
    """Link to the published records"""

    html: URL | None = field(default=None)
    """Link to the model records' HTML listing page"""

    drafts: Optional[URL] = field(default=None)
    """Link to the user's draft records"""

    deposit: Optional[URL] = field(default=None)
    """Deposition link for the model"""

    model: URL | None = field(default=None)
    """Link to the model definition"""


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class ModelInfoContentType(Model):
    """Acceptable content-types for the model."""

    content_type: str
    """The content-type accepted by the model"""

    name: str | None = None
    """The name of the content-type"""

    description: str | None = None
    """The description of the content-type"""

    schema: URL | None = None
    """Machine parseable schema for the content-type"""
    
    can_export: bool = False
    """Whether the content-type can be used for exporting records (via Accept header)"""
    
    can_deposit: bool = False
    """Whether the content-type can be used for importing records (via Content-Type header)"""


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class ModelInfo(Model):
    """Information about metadata model within invenio server."""

    type: str
    """The type of the model"""

    schema: str
    """The json schema of the model"""

    name: str
    """The name of the model"""

    description: str
    """The description of the model"""

    version: str
    """The version of the model"""

    features: list[str]
    """List of features supported by the model"""

    links: ModelInfoLinks
    """Links to the model"""

    content_types: list[ModelInfoContentType] = field(factory=list)
    """List of supported content-types for API serialization"""

    metadata: bool = field(default=True)
    """Whether the model contains metadata inside the metadata element."""


@extend_serialization(allow_extra_data=True)
@define(kw_only=True)
class RepositoryInfo(Model):
    """Extra info downloaded from nrp-compatible invenio repository."""

    schema: str
    """Version of this configuration schema"""

    name: str
    """The name of the repository"""

    description: str
    """The description of the repository"""

    version: str
    """The version of the repository"""

    invenio_version: str
    """The version of invenio the repository is based on"""

    links: RepositoryInfoLinks
    """Links to the repository"""

    transfers: list[str] = field(factory=list)
    """List of supported file transfer protocols"""

    models: dict[str, ModelInfo] = field(factory=dict)
    """Information about the models in the repository"""

    default_model: str | None = field(default=None)
    """The default model for the repository. 
    If set, it is used whenever the model is not specified."""

    features: list[str] = field(factory=list)
    """List of features supported by the repository"""

    default_content_type: str = "application/json"
    """Default content type for accessing/uploading the records in the repository."""
