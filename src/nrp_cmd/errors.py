#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Errors raised from invenio repository."""

import json
from typing import Any


class RepositoryError(Exception):
    """Base class for all repository errors."""

    pass


class RepositoryCommunicationError(RepositoryError):
    """Base class for all repository communication errors."""


class RepositoryNetworkError(RepositoryCommunicationError):
    """Raised when a network error occurs."""


class RepositoryJSONError(RepositoryCommunicationError):
    """Raised from a repository when an error occurs."""

    def __init__(self, request_info: Any, response: dict[str, Any]):  # noqa ANN401
        """Initialize the error."""
        self._request_info = request_info
        self._response = response

    @property
    def request_info(self) -> Any:
        """Return the request info."""
        return self._request_info

    @property
    def json(self) -> dict[str, Any]:
        """Return the JSON response."""
        return self._response

    def __repr__(self) -> str:
        """Return the representation of the error."""
        return f"{self._request_info.url} : {json.dumps(self.json)}"

    def __str__(self) -> str:
        """Return the string representation of the error."""
        return self.__repr__()


class RepositoryServerError(RepositoryJSONError):
    """An error occurred on the server side (5xx http status code)."""


class RepositoryClientError(RepositoryJSONError):
    """An error occurred on the client side (4xx http status code).

    This is usually not found, unauthorized, malformed request and similar.
    """

class DoesNotExistError(RepositoryClientError):
    pass

class RepositoryRetryError(Exception):
    def __init__(self, after_seconds: float | None = None):
        self.after_seconds = after_seconds


class UnstructureError(Exception):
    pass


class StructureError(Exception):
    pass


def is_instance_of_exceptions(
    exception: Any, exceptions: tuple[type[Exception], ...] | type[Exception]
) -> bool:  
    # Check if the current exception is an instance of T
    if isinstance(exception, exceptions):
        return True

    # Handle ExceptionGroup (Python 3.11+)
    if isinstance(exception, BaseExceptionGroup):
        sub_exception: Any
        for sub_exception in exception.exceptions:  # type: ignore
            if is_instance_of_exceptions(sub_exception, exceptions):
                return True

    # Check chained exceptions (__cause__ or __context__)
    if exception.__cause__ is not None and is_instance_of_exceptions(
        exception.__cause__, exceptions
    ):
        return True
    if exception.__context__ is not None and is_instance_of_exceptions(
        exception.__context__, exceptions
    ):
        return True

    return False
