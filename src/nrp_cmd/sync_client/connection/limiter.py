#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Contains the limiter class for limiting the number of simultaneous connections.

Note: the limiter is not propagated to created threads - each thread has by default
its own limiter with the default capacity of 10 connections.

Use LimitedThread to create a thread with the same limiter as the parent thread.
"""

import contextlib
import contextvars
from collections.abc import Generator
from threading import Lock, Semaphore, Thread

from yarl import URL

limiter_lock = Lock()


class Limiter(Semaphore):
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

    @contextlib.contextmanager
    def limit(self, url: URL):
        with self:
            yield

current_limiter_var = contextvars.ContextVar[Limiter](
    "current_limiter", default=Limiter(10)
)

class CurrentLimiterProxy:
    """A class to manage the current limiter."""

    @property
    def free(self) -> int:
        """The number of free slots.

        :return:   the number of remaining connections (approximate)
        """
        return current_limiter_var.get().free

    @contextlib.contextmanager
    def limit(self, url: URL):
        try:
            limiter = current_limiter_var.get()
        except LookupError:
            limiter = None
        if limiter is None:
            limiter = Limiter(10)
            current_limiter_var.set(limiter)

        with limiter.limit(url):
            yield

    def reset(self):
        """Reset the current limiter."""
        current_limiter_var.set(None)


current_limiter = CurrentLimiterProxy()

@contextlib.contextmanager
def limit_connections(
    max_connections: int, per_server_connections: int = -1
) -> Generator[None, None, None]:
    """Limit the number of connections called in the context of the with statement."""
    token = current_limiter_var.set(Limiter(max_connections, per_server_connections))
    try:
        yield
    finally:
        current_limiter_var.reset(token)


class LimitedThread(Thread):
    """A thread with a limited number of connections."""

    def __init__(self, *args, **kwargs):
        self.ctx = contextvars.copy_context()
        super().__init__(*args, **kwargs)

    def run(self):
        # This code runs in the target, child class:
        self.ctx.run(super().run)
