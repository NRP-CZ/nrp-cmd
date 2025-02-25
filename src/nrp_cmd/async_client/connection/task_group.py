#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Asynchronous task group."""

import asyncio
from collections.abc import Callable, Coroutine
from contextvars import Context
from typing import Any


class TaskGroup(asyncio.TaskGroup):
    """Compatibility layer for TaskGroup.

    Using factory for coro so that we can have a similar API to the sync version.
    """

    def create_task[_T](  # type: ignore
        self,
        coro: Callable[[], Coroutine[Any, Any, _T]],
        *,
        name: str | None = None,
        context: Context | None = None,
    ) -> asyncio.Task[_T]:
        return super().create_task(coro(), name=name, context=context)

Task = asyncio.Task

__all__ = ("TaskGroup", "Task")