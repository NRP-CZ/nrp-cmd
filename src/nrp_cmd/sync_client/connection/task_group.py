#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Synchronous task group."""

from collections.abc import Callable


class TaskResult[T]:
    """Synchronous version of TaskResult."""

    def __init__(self, result: T):
        self._result = result

    def result(self) -> T:
        return self._result


class TaskGroup:
    """Synchronous version of TaskGroup."""

    def create_task[_T](  # type: ignore
        self,
        task: Callable[[], _T],
    ) -> TaskResult[_T]:
        return TaskResult(task())
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

Task = None

__all__ = ("TaskGroup", "Task")
