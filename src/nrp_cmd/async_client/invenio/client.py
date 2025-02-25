"""Invenio asynchronous client."""

from typing import Any, Self, override

from yarl import URL  # noqa: TCH002    as attrs need to have type info in runtime

from ...config import RepositoryConfig
from ...errors import (
    RepositoryClientError,
    RepositoryCommunicationError,
    StructureError,
    is_instance_of_exceptions,
)
from ...rdm_compat import make_rdm_info
from ...types.info import ModelInfo, RepositoryInfo
from ..base_client import AsyncRepositoryClient
from ..connection import AsyncConnection
from .files import AsyncInvenioFilesClient
from .records import AsyncInvenioRecordsClient
from .requests import AsyncInvenioRequestsClient


class AsyncInvenioRepositoryClient(AsyncRepositoryClient):
    """An abstract client for NRP repositories.

    Usually, subclasses of this class are not instantiated directly in your code.
    To get an instance of a repository, use the high-level method `get_async_client`:

    ```
    my_client = await async_client(config?, url=url, refresh=False/True)
    my_client = await async_client(config?, alias=alias, refresh=False/True)
    ```

    and then use the instance.
    """

    @override
    @classmethod
    async def can_handle_repository(
        cls, url: URL | str, verify_tls: bool = True
    ) -> URL | None:
        connection = AsyncConnection(verify_tls=verify_tls)
        if isinstance(url, str):
            url = URL(url)

        # check if the repository is an NRP invenio repository
        well_known_url = url.with_path("/.well-known/repository")
        try:
            data = await connection.get(url=well_known_url, result_class=dict[str, Any])
            if "invenio_version" in data:
                if "api" in data.get("links", {}):
                    return URL(data["links"]["api"])
                # fallback for older oarepo-runtime versions
                return url.with_path("/api")
        except Exception:
            pass

        # check if the repository is a plain Invenio RDM repository, such as zenodo
        try:
            root_page_data = await connection.get(url=url.with_path("/"), result_class=str)
            if '<meta name="generator" content="InvenioRDM' in root_page_data:
                return url.with_path("/api")
        except Exception:
            pass
        return None

    @override
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
        ret = cls(config=config, extra_tokens=extra_tokens)
        if refresh or not config.info:
            config.info = await ret.get_repository_info(refresh=True)
        return ret

    def __init__(
        self,
        config: RepositoryConfig,
        extra_tokens: dict[URL, str] | None = None,
    ):
        """Create a new client for the given repository configuration."""
        self._config = config
        tokens: dict[URL, str] = {}
        if extra_tokens:
            tokens.update(extra_tokens)
        if config.token:
            tokens[config.url] = config.token
        self._connection = AsyncConnection(
            tokens=tokens,
            verify_tls=config.verify_tls,
            retry_count=config.retry_count,
            retry_after_seconds=config.retry_after_seconds,
        )

    @override
    async def get_repository_info(self, refresh: bool = True) -> RepositoryInfo:
        if self._config.info and not refresh:
            return self._config.info

        try:
            info = await self._connection.get(
                url=self._config.well_known_repository_url,
                result_class=RepositoryInfo,
            )
            self._config.info = info

            if not self._config.info.links.models:
                raise ValueError("The repository does not provide the models link.")

            models = await self._connection.get(
                url=self._config.info.links.models,
                result_class=list[ModelInfo],
            )

            info.models = {
                model.type: model for model in models
            }

        except* (RepositoryClientError, RepositoryCommunicationError) as exc:
            if is_instance_of_exceptions(exc, StructureError):
                raise exc
            # not a NRP based repository, suppose that it is plain invenio rdm
            info = self._config.info = make_rdm_info(self._config.url)

        return info

    @property
    @override
    def records(self) -> AsyncInvenioRecordsClient:
        """Return client for accessing records."""
        assert self._config.info, "Repository info is not available, can not create records client."
        return AsyncInvenioRecordsClient(
            self._connection, self._config.info, self.requests
        )

    @property
    @override
    def files(self) -> AsyncInvenioFilesClient:
        """Return client for accessing records."""
        assert self._config.info, "Repository info is not available, can not create records client."
        return AsyncInvenioFilesClient(self._connection, self._config.info)

    @property
    @override
    def requests(self) -> AsyncInvenioRequestsClient:
        """Return client for accessing requests."""
        assert (
            self._config.info
        ), "Repository info is not available, can not create requests client."
        return AsyncInvenioRequestsClient(self._connection, self._config.info)
