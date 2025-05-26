#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Asynchronous connection for the NRP client using the aiohttp library."""

import asyncio
import contextlib
import inspect
import json as _json
import logging
from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
)
from functools import partial
from typing import Any, Literal, Optional, cast, overload

from aiohttp import ClientResponse, ClientSession, TCPConnector
from aiohttp.client_exceptions import ClientConnectorError
from cattrs.dispatch import UnstructureHook
from multidict import CIMultiDictProxy, MultiDictProxy
from yarl import URL

from ...converter import deserialize_rest_response
from ...errors import (
    RepositoryClientError,
    RepositoryCommunicationError,
    RepositoryError,
    RepositoryRetryError,
    StructureError,
    is_instance_of_exceptions,
)
from ...progress import DummyProgressBar, ProgressBar, current_progress
from ..streams.base import DataSink, DataSource
from ..streams.progress import ProgressSink
from .auth import AuthenticatedClientRequest, BearerAuthentication, BearerTokenForHost
from .aws_limits import MINIMAL_DOWNLOAD_PART_SIZE, adjust_download_multipart_params
from .limiter import current_limiter
from .response import RepositoryResponse

log = logging.getLogger("invenio_nrp.async_client.connection")
communication_log_url = logging.getLogger("nrp_cmd.communication.url")
communication_log_request = logging.getLogger("nrp_cmd.communication.request")
communication_log_response = logging.getLogger("nrp_cmd.communication.response")


class try_until_success:

    def __init__(
        self,
        attempts: int,
        retry_interval: int,
        too_many_requests_retry_count: int = 5,
        quiet: bool = False,
    ):
        self.attempts = attempts
        self.attempt = 0
        self.too_many_requests_attempts = too_many_requests_retry_count
        self.done = False
        self.failures: list[Exception] = []
        self.retry_interval = retry_interval
        self.current_sleep_interval = 0
        self.quiet = quiet

    async def __aiter__(self):
        while not self.done and self.attempt < self.attempts:
            yield self
            if not self.done:
                log.error(
                    "Retrying %s of %s. Will retry in %s seconds. Latest error: %s...",
                    self.attempt,
                    self.attempts,
                    self.current_sleep_interval,
                    str(self.failures[-1])[:40],
                )
                await asyncio.sleep(self.current_sleep_interval)

        if self.done:
            return

        if self.failures:
            raise ExceptionGroup("Failures in HTTP transport", self.failures)

    async def __aenter__(self):
        self.attempt += 1

    async def __aexit__(self, _ext, exc, _tb):  # type: ignore
        if exc:
            self.failures.append(cast("Exception", exc))
            if isinstance(exc, RepositoryRetryError):
                # if too many requests, we can repeat,
                # so try again and do not add the attempt
                if self.too_many_requests_attempts:
                    self.too_many_requests_attempts -= 1
                    self.attempt -= 1
                if exc.after_seconds is not None:
                    self.current_sleep_interval = exc.after_seconds + 1
                    return True
                self.current_sleep_interval = self.retry_interval * (self.attempt + 1)
                return True

            if is_instance_of_exceptions(exc, (RepositoryClientError, StructureError)):
                return False
            else:
                self.current_sleep_interval = self.retry_interval * (self.attempt + 1)
                return True

        self.done = True


@contextlib.asynccontextmanager
async def _cast_error() -> AsyncIterator[None]:
    """Catch all errors and cast them to Repository*Error."""
    try:
        yield
    except RepositoryError:
        raise
    except RepositoryRetryError:
        raise
    except ClientConnectorError:
        raise
    except Exception as e:
        raise RepositoryCommunicationError(str(e)) from e


class AsyncConnection:
    """Pre-configured asynchronous http connection."""

    def __init__(
        self,
        *,
        tokens: dict[URL, str] | None = None,
        verify_tls: bool = True,
        retry_count: int = 5,
        retry_after_seconds: int = 1,
    ):
        """Create a new connection with the given configuration."""
        self._verify_tls = verify_tls
        self._retry_count = retry_count
        self._retry_after_seconds = retry_after_seconds

        _tokens: list[BearerTokenForHost] = [
            BearerTokenForHost(host_url=url, token=token)
            for url, token in (tokens or {}).items()
            if token
        ]
        self._auth = BearerAuthentication(_tokens)

    @contextlib.asynccontextmanager
    async def _client(
        self, idempotent: bool = False
    ) -> AsyncGenerator[ClientSession, None]:
        """Create a new session with the repository and configure it with the token.

        :return: A new http client
        """
        """
        Create a new session with the repository and configure it with the token.
        :return: A new http client
        """

        connector = TCPConnector(verify_ssl=self._verify_tls)
        async with ClientSession(
            request_class=AuthenticatedClientRequest,
            response_class=RepositoryResponse,
            connector=connector,
            raise_for_status=False,
        ) as session:
            yield session

    @overload
    async def head(
        self,
        *,
        url: URL,
        use_get: bool = False,
        get_links: Literal[False],
        **kwargs: Any,  # noqa: ANN401
    ) -> CIMultiDictProxy[str]: ...

    @overload
    async def head(
        self,
        *,
        url: URL,
        use_get: bool = False,
        get_links: Literal[True],
        **kwargs: Any,  # noqa: ANN401
    ) -> MultiDictProxy[MultiDictProxy[str | URL]]: ...

    async def head(
        self,
        *,
        url: URL,
        use_get: bool = False,
        get_links: bool = False,
        **kwargs: Any,  # noqa: ANN401
    ) -> CIMultiDictProxy[str] | MultiDictProxy[MultiDictProxy[str | URL]]:
        """Perform a HEAD request to the repository.

        :param url:                 the url of the request
        :param idempotent:          True if the request is idempotent, should be for HEAD requests
        :param kwargs:              any kwargs to pass to the aiohttp client
        :return:                    None

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network
        """

        async def _head(
            response: ClientResponse,
        ) -> CIMultiDictProxy[str] | MultiDictProxy[MultiDictProxy[str | URL]]:
            await response.raise_for_invenio_status()
            if get_links:
                return response.links
            return response.headers

        with current_progress.short_task():
            if use_get:
                return await self._retried(
                    "GET", url, _head, idempotent=True, headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"}
                )
            else:
                return await self._retried("HEAD", url, _head, idempotent=True, headers={"Accept-Encoding": "identity"})

    async def get[T](
        self,
        *,
        url: URL,
        result_class: type[T],
        **kwargs: Any,  # noqa: ANN401
    ) -> T:
        """Perform a GET request to the repository.

        :param url:                 the url of the request
        :param idempotent:          True if the request is idempotent, should be for GET requests
        :param result_class:        successful response will be parsed to this class
        :param kwargs:              any kwargs to pass to the aiohttp client
        :return:                    the parsed result

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network error
        """
        with current_progress.short_task():
            return await self._retried(
                "GET",
                url,
                partial(
                    self._get_call_result,
                    result_class=result_class,
                ),
                idempotent=True,
                **kwargs,
            )

    async def post[T](
        self,
        *,
        url: URL,
        json: dict[str, Any] | list[Any] | None = None,
        data: bytes | None = None,
        idempotent: bool = False,
        result_class: type[T],
        **kwargs: Any,  # noqa: ANN401
    ) -> T:
        """Perform a POST request to the repository.

        :param url:                 the url of the request
        :param json:                the json payload of the request (use exactly one of json or data)
        :param data:                the data payload of the request
        :param idempotent:          True if the request is idempotent, normally should be False
        :param result_class:        successful response will be parsed to this class
        :param kwargs:              any kwargs to pass to the aiohttp client
        :return:                    the parsed result

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network
        """
        assert (
            json is not None or data is not None
        ), "Either json or data must be provided"

        with current_progress.short_task():
            return await self._retried(
                "POST",
                url,
                partial(
                    self._get_call_result,
                    result_class=result_class,
                ),
                idempotent=idempotent,
                json=json,
                data=data,
                **kwargs,
            )

    async def put[T](
        self,
        *,
        url: URL,
        json: dict[str, Any] | list[Any] | None = None,
        data: bytes | None = None,
        result_class: type[T],
        **kwargs: Any,  # noqa: ANN401
    ) -> T:
        """Perform a PUT request to the repository.

        :param url:                     the url of the request
        :param json:                    the json payload of the request (use exactly one of json or data)
        :param data:                    the data payload of the request
        :param result_class:            successful response will be parsed to this class
        :param kwargs:                  any kwargs to pass to the aiohttp client
        :return:                        the parsed result

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network
        """
        assert (
            json is not None or data is not None
        ), "Either json or data must be provided"

        with current_progress.short_task():
            return await self._retried(
                "PUT",
                url,
                partial(
                    self._get_call_result,
                    result_class=result_class,
                ),
                idempotent=True,
                json=json,
                data=data,
                **kwargs,
            )

    async def put_stream(
        self,
        *,
        url: URL,
        source: DataSource,
        open_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> ClientResponse:
        """Perform a PUT request to the repository with a file.

        :param url:                 the url of the request
        :param file:                the file to send
        :param kwargs:              any kwargs to pass to the aiohttp client
        :return:                    the response (not parsed)

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network
        """

        async def _put(response: ClientResponse) -> ClientResponse:
            return response

        with current_progress.short_task():
            return await self._retried(
                "PUT",
                url,
                _put,
                idempotent=True,
                data=partial(source.open, **(open_kwargs or {})),
                **kwargs,
            )

    async def get_stream(
        self,
        *,
        url: URL,
        sink: DataSink,
        offset: int = 0,
        size: int | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Perform a GET request to the repository and write the response to a sink.

        :param url:                 the url of the request
        :param kwargs:              any kwargs to pass to the aiohttp client
        :return:                    the parsed result

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network error
        """

        async def _copy_stream(response: ClientResponse) -> None:
            chunk = await sink.open_chunk(offset=offset)
            try:
                async for data in response.content.iter_any():
                    await chunk.write(data)
            finally:
                await chunk.close()

        if size is not None:
            range_header = f"bytes={offset}-{offset + size - 1}"
        else:
            range_header = f"bytes={offset}-"

        with current_progress.short_task():
            await self._retried(
                "GET",
                url,
                _copy_stream,
                idempotent=True,
                headers={"Range": range_header},
                **kwargs,
            )

    async def delete(
        self,
        *,
        url: URL,
        idempotent: bool = False,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Perform a DELETE request to the repository.

        :param url:                 the url of the request
        :param idempotent:          True if the request is idempotent, normally should be False
        :param kwargs:              any kwargs to pass to the aiohttp client
        :return:                    None

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network
        """
        with current_progress.short_task():
            return await self._retried(
                "DELETE", url, None, idempotent=idempotent, **kwargs
            )

    @overload
    async def _get_call_result[T](
        self,
        response: ClientResponse,
        result_class: type[T],
    ) -> T: ...

    @overload
    async def _get_call_result(
        self,
        response: ClientResponse,
        result_class: None,
    ) -> None: ...

    async def _get_call_result[T](
        self,
        response: ClientResponse,
        result_class: type[T] | None,
    ) -> T | None:
        """Get the result from the response.

        :param response:            the aiohttp response
        :param result_class:        the class to parse the response to
        :return:                    the parsed result

        :raises RepositoryClientError: if the request fails due to client passing incorrect parameters (HTTP 4xx)
        :raises RepositoryServerError: if the request fails due to server error (HTTP 5xx)
        :raises RepositoryCommunicationError: if the request fails due to network
        """
        if response.status != 204:
            json_payload = await response.read()
        else:
            json_payload = b""

        if communication_log_response.isEnabledFor(logging.INFO):
            communication_log_response.info(
                "%s", _json.dumps(_json.loads(json_payload))
            )

        await response.raise_for_invenio_status()  # type: ignore
        if response.status == 204:
            assert result_class is None
            return None

        assert result_class is not None
        if inspect.isclass(result_class):
            if issubclass(result_class, ClientResponse):
                return cast("T", response)  # mypy can not get it
            elif issubclass(result_class, str):
                return cast("T", json_payload.decode("utf-8"))  # mypy can not get it
            elif issubclass(result_class, dict):
                return _json.loads(json_payload)
        etag = remove_quotes(response.headers.get("ETag"))
        return deserialize_rest_response(self, json_payload, result_class, etag)

    @overload
    async def _retried[T](
        self,
        method: str,
        url: URL,
        callback: Callable[[ClientResponse], Awaitable[T]],
        idempotent: bool,
        **kwargs: Any,  # noqa: ANN401
    ) -> T: ...

    @overload
    async def _retried(
        self,
        method: str,
        url: URL,
        callback: None,
        idempotent: bool,
        **kwargs: Any,  # noqa: ANN401
    ) -> None: ...

    async def _retried[T](
        self,
        method: str,
        url: URL,
        callback: Callable[[ClientResponse], Awaitable[T]] | None,
        idempotent: bool,
        **kwargs: Any,  # noqa: ANN401
    ) -> T | None:
        """Log the start of a request and retry it if necessary."""
        json = kwargs.get("json")
        if json is not None and callable(json):
            json = json()
            kwargs["json"] = json

        data = kwargs.get("data")

        async for attempt in try_until_success(
            self._retry_count if idempotent else 1, self._retry_after_seconds
        ):
            actual_data = None
            if (
                data is not None
                and callable(data)
                and inspect.iscoroutinefunction(data)
            ):
                actual_data = await data()
                kwargs["data"] = actual_data
            try:

                @contextlib.asynccontextmanager
                async def print_log():
                    if communication_log_url.isEnabledFor(logging.INFO):
                        communication_log_url.info("%s %s", method.upper(), url)
                    if communication_log_request.isEnabledFor(logging.INFO):
                        if json is not None:
                            communication_log_request.info("%s", _json.dumps(json))
                        if data is not None:
                            communication_log_request.info("(stream)")
                    yield

                async with (
                    attempt,
                    current_limiter.limit(url),
                    self._client(idempotent=True) as client,
                    _cast_error(),
                    print_log(),
                    client.request(method, url, auth=self._auth, **kwargs) as response,
                ):
                    if callback is not None:
                        return await callback(response)
                    else:
                        await response.raise_for_invenio_status()  # type: ignore
                    return None
            finally:
                if actual_data is not None and hasattr(actual_data, "close"):
                    await actual_data.close()

        raise Exception("unreachable")

    async def download_file(
        self,
        url: URL,
        sink: DataSink,
        parts: int | None = None,
        part_size: int | None = None,
        progress_bar: ProgressBar | None = None,
    ) -> None:
        progress_bar = progress_bar or DummyProgressBar()

        try:
            headers = await self.head(url=url, get_links=False)
        except RepositoryClientError:
            # The file is not available for HEAD. This is the case for S3 files
            # where the file is a pre-signed request. We'll try to download the headers
            # with a GET request with a range header containing only the first byte.
            headers = await self.head(url=url, use_get=True, get_links=False)

        size = 0
        location = URL(headers.get('Location', url))

        if "Content-Range" in headers:
            size = int(headers["Content-Range"].split("/")[-1])
        elif "Content-Length" in headers:
            size = int(headers["Content-Length"])

        if size:
            await sink.allocate(size)
            progress_bar.set_total(size)

        if (
            size
            and size > MINIMAL_DOWNLOAD_PART_SIZE
            and any(x == "bytes" for x in headers.getall("Accept-Ranges", []))
        ):
            await self._download_multipart(
                location, sink, size, progress_bar, parts, part_size
            )
        else:
            await self._download_single(location, sink, progress_bar)

    async def _download_single(
        self, url: URL, sink: DataSink, progress_bar: ProgressBar
    ) -> None:
        await self.get_stream(url=url, sink=ProgressSink(sink, progress_bar), offset=0)

    async def _download_multipart(
        self,
        url: URL,
        sink: DataSink,
        size: int,
        progress_bar: ProgressBar,
        parts: int | None = None,
        part_size: int | None = None,
    ) -> None:
        adjusted_part_size, adjusted_parts = adjust_download_multipart_params(
            size, parts, part_size
        )

        async with asyncio.TaskGroup() as tg:
            for i in range(adjusted_parts):
                start = i * adjusted_part_size
                part_size = min((i + 1) * adjusted_part_size, size) - start
                tg.create_task(
                    self.get_stream(
                        url=url,
                        sink=ProgressSink(sink, progress_bar),
                        offset=start,
                        size=part_size,
                    )
                )


def remove_quotes(etag: str | None) -> Optional[str]:
    """Remove quotes from an etag.

    :param etag:    the etag header
    :return:        the etag without quotes
    """
    if etag is None:
        return None
    if etag.startswith("W/"):
        etag = etag[2:]
    return etag.strip('"')


def connection_unstructure_hook(data: Any, previous: UnstructureHook) -> Any:
    ret = previous(data)
    ret.pop("_connection", None)
    ret.pop("_etag", None)
    return ret


__all__ = ("AsyncConnection",)
