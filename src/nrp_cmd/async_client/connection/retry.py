#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Implementation of 429 retry strategy for aiohttp."""

from typing import Any, Optional

from aiohttp import ClientResponse
from aiohttp_retry import ExponentialRetry


class ServerAssistedRetry(ExponentialRetry):
    """A retry strategy that uses the Retry-After header for 429 responses."""

    def __init__(self, **kwargs: Any):  # noqa: ANN401
        """Initialize the retry strategy."""
        kwargs.setdefault("factor", 1.5)
        if "max_timeout" not in kwargs:
            start_timeout = kwargs.get("start_timeout", 5)
            retry_count = kwargs.get("attempts", 5)
            max_timeout = retry_count * retry_count * start_timeout
            kwargs["max_timeout"] = max_timeout
            kwargs["retry_all_server_errors"] = False
        super().__init__(**kwargs)

    def get_timeout(
        self, attempt: int, response: Optional[ClientResponse] = None
    ) -> float:
        """Get the timeout for the next retry.

        :param attempt: The number of the current attempt.
        :param response: The response of the last request.
        """
        if response and response.status == 429:
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header:
                return float(retry_after_header) + 1
        return super().get_timeout(attempt, response)
