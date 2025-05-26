#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Configuration of the repository and repository access classes."""

from typing import Optional

from attrs import define
from yarl import URL

from ..types.info import RepositoryInfo


@define(kw_only=True)
class RepositoryConfig:
    """Configuration of the repository."""

    alias: str
    """The local alias of the repository."""

    url: URL
    """The api URL of the repository, usually something like https://repository.org/api."""

    token: Optional[str] = None
    """Bearer token"""

    verify_tls: bool = True
    """Verify the TLS certificate in https"""

    retry_count: int = 10
    """Number of times idempotent operations will be retried if something goes wrong."""

    retry_after_seconds: int = 10
    """If server does not suggest anything else, retry after this interval in seconds"""

    info: RepositoryInfo | None = None
    """Cached repository info"""

    enabled: bool = True
    """Whether the repository is enabled in the configuration.
    
    If the repository is not enabled, it will not be used by the client
    even if user wants to access URL that points to the repository.
    This is useful for disabling repositories that are not available
    or are not supposed to be used at the moment or switching between
    testing repositories that live on the same URL but have different
    credentials.
    """

    class Config:  # noqa
        extra = "forbid"

    @property
    def well_known_repository_url(self) -> URL:
        """Return URL to the well-known repository endpoint."""
        return self.url / ".well-known" / "repository/"

    def search_url(self, model: str | None) -> URL:
        """Return URL to search for published records within a model."""
        assert self.info is not None
        model = model or self._default_model_name
        if model:
            return self.info.models[model].links.published
        return self.info.links.records

    def user_search_url(self, model: str | None) -> URL:
        """Return URL to search for user's records within a model."""
        assert self.info is not None
        model = model or self._default_model_name
        if model:
            user_records = self.info.models[model].links.user_records
            if user_records is None:
                return self.search_url(model)
            return user_records
        return self.info.links.user_records

    def create_url(self, model: str | None) -> URL:
        """Return URL to create a new record within a model."""
        assert self.info is not None
        model = model or self._default_model_name
        if model:
            return self.info.models[model].links.api
        return self.info.links.records

    def read_url(self, model: str | None, record_id: str | URL) -> URL:
        """Return URL to a published record within a model."""
        assert self.info is not None
        if isinstance(record_id, URL):
            return record_id
        if record_id.startswith("https://"):
            return URL(record_id)
        model = model or self._default_model_name
        if model:
            return self.info.models[model].links.api / record_id
        return self.info.links.records / record_id

    def user_read_url(self, model: str | None, record_id: str | URL) -> URL:
        """Return URL to a draft record within a model."""
        assert self.info is not None
        if isinstance(record_id, URL):
            return record_id
        if record_id.startswith("https://"):
            return URL(record_id)
        model = model or self._default_model_name
        if model:
            return self.info.models[model].links.api / record_id / "draft"
        return self.info.links.records / record_id / "draft"

    @property
    def requests_url(self) -> URL:
        """Return URL to the requests endpoint."""
        assert self.info is not None
        return self.info.links.requests

    @property
    def _default_model_name(self) -> str | None:
        """Return the default model name if there is only one model in the repository."""
        if self.info and len(self.info.models) == 1:
            return next(iter(self.info.models))
        return None
