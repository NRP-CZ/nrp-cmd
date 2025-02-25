#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Contains the limiter class for limiting the number of simultaneous connections."""

import asyncio
import contextlib
import contextvars
from collections.abc import AsyncGenerator, Generator

from yarl import URL


class Limiter(asyncio.Semaphore):
    """A class to limit the number of simultaneous connections."""

    def __init__(self, capacity: int, per_server_capacity: int = -1):
        """Initialize the limiter.

        :param capacity:    the number of simultaneous connections
        """
        if capacity <= 0:
            capacity = 10
        self.capacity = capacity
        super().__init__(capacity)

    @property
    def free(self) -> int:
        """The number of free slots.

        :return:   the number of remaining connections (approximate)
        """
        return self._value

    @contextlib.asynccontextmanager
    async def limit(self, url: URL) -> AsyncGenerator[None, None]:
        async with self:
            yield


current_limiter_var = contextvars.ContextVar[Limiter]("current_limiter")


class CurrentLimiterProxy:
    """A class to manage the current limiter."""

    @property
    def free(self) -> int:
        """The number of free slots.

        :return:   the number of remaining connections (approximate)
        """
        return current_limiter_var.get().free

    @contextlib.asynccontextmanager
    async def limit(self, url: URL) -> AsyncGenerator[None, None]:
        try:
            limiter = current_limiter_var.get()
        except LookupError:
            limiter = None
        if limiter is None:
            limiter = Limiter(10)
            current_limiter_var.set(limiter)
        async with limiter.limit(url):
            yield

    def reset(self):
        """Reset the current limiter."""
        current_limiter_var.set(None)

current_limiter = CurrentLimiterProxy()

@contextlib.contextmanager
def limit_connections(
    max_connections: int, per_server_connections: int = -1
) -> Generator[None, None, None]:
    """Limit the number of simultaneous connections."""
    token = current_limiter_var.set(Limiter(max_connections, per_server_connections))
    try:
        yield
    finally:
        current_limiter_var.reset(token)